"""
Booking service layer — the core booking engine.

Handles the complete booking lifecycle with concurrency-safe
inventory management using pessimistic locking.
"""

import logging
from datetime import date

from django.db import transaction
from django.utils import timezone

from apps.common.exceptions import (
    BadRequestException,
    BookingException,
    ForbiddenException,
    InventoryException,
    ResourceNotFoundException,
)
from apps.inventory.services import InventoryService
from apps.pricing.services import PricingService

from .models import Booking, BookingGuest, BookingStatus

logger = logging.getLogger(__name__)


class BookingService:
    """Core booking engine with concurrency-safe operations."""

    @staticmethod
    def get_booking_or_404(booking_id: int) -> Booking:
        """Retrieve a booking by ID or raise 404."""
        try:
            return Booking.objects.select_related(
                "hotel", "room", "user", "payment"
            ).get(id=booking_id)
        except Booking.DoesNotExist:
            raise ResourceNotFoundException(f"Booking #{booking_id} not found.")

    @staticmethod
    def initialize_booking(
        user,
        room_id: int,
        check_in: date,
        check_out: date,
    ) -> Booking:
        """
        Initialize a new booking (Step 1 of the booking flow).

        This is the most critical operation — it uses pessimistic locking
        to prevent double bookings.

        Flow:
            1. Open transaction with atomic()
            2. Lock inventory rows with select_for_update()
            3. Validate availability on all dates
            4. Increment booked_count on each row
            5. Calculate total price
            6. Create Booking with status RESERVED

        Args:
            user: The user making the booking
            room_id: ID of the room type to book
            check_in: Check-in date
            check_out: Check-out date

        Returns:
            Booking instance with status RESERVED
        """
        # Validate dates
        if check_in >= check_out:
            raise BadRequestException("Check-out date must be after check-in date.")
        if check_in < date.today():
            raise BadRequestException("Check-in date cannot be in the past.")

        # Get the room
        from apps.rooms.models import Room
        try:
            room = Room.objects.select_related("hotel").get(id=room_id)
        except Room.DoesNotExist:
            raise ResourceNotFoundException(f"Room with id {room_id} not found.")

        if not room.hotel.active:
            raise BadRequestException("This hotel is not currently active.")

        # === CRITICAL SECTION: Pessimistic locking ===
        with transaction.atomic():
            # Step 1: Lock inventory rows — blocks other concurrent transactions
            inventory_rows = InventoryService.find_and_lock_available_inventory(
                room_id=room_id,
                check_in=check_in,
                check_out=check_out,
            )

            # Step 2: Reserve inventory (increment booked_count)
            InventoryService.reserve_inventory(inventory_rows)

            # Step 3: Calculate total price using dynamic pricing
            total_price = PricingService.calculate_total_stay_price(
                room=room,
                check_in=check_in,
                check_out=check_out,
                inventory_rows=inventory_rows,
            )

            # Step 4: Create the booking
            booking = Booking.objects.create(
                hotel=room.hotel,
                room=room,
                user=user,
                check_in_date=check_in,
                checkout_date=check_out,
                status=BookingStatus.RESERVED,
                total_price=total_price,
            )

        logger.info(
            "Booking #%d created: room=%d, dates=%s to %s, price=$%.2f",
            booking.id, room_id, check_in, check_out, total_price,
        )
        return booking

    @staticmethod
    def add_guests(booking_id: int, guest_ids: list, user) -> Booking:
        """
        Add guests to a booking (Step 2 of the booking flow).

        Validates:
            - Booking belongs to the user
            - Booking is in RESERVED status
            - Guests belong to the user
            - Number of guests doesn't exceed room capacity
        """
        booking = BookingService.get_booking_or_404(booking_id)

        # Verify ownership
        if booking.user != user:
            raise ForbiddenException("You do not own this booking.")

        # Verify state
        if booking.status not in (BookingStatus.RESERVED, BookingStatus.GUESTS_ADDED):
            raise BookingException(
                f"Cannot add guests to a booking in '{booking.status}' status."
            )

        # Validate guests belong to user
        from apps.users.models import Guest
        guests = Guest.objects.filter(id__in=guest_ids, user=user)
        if len(guests) != len(guest_ids):
            raise BadRequestException("One or more guest IDs are invalid.")

        # Check capacity
        if len(guest_ids) > booking.room.capacity:
            raise BadRequestException(
                f"Too many guests. Room capacity is {booking.room.capacity}."
            )

        # Clear existing and add new
        BookingGuest.objects.filter(booking=booking).delete()
        booking_guests = [
            BookingGuest(booking=booking, guest=guest)
            for guest in guests
        ]
        BookingGuest.objects.bulk_create(booking_guests)

        # Transition status
        if booking.status == BookingStatus.RESERVED:
            booking.transition_to(BookingStatus.GUESTS_ADDED)

        logger.info(
            "Guests added to booking #%d: %s",
            booking.id, guest_ids,
        )
        return booking

    @staticmethod
    def cancel_booking(booking_id: int, user) -> Booking:
        """
        Cancel a booking and release inventory.

        Can be called from RESERVED, GUESTS_ADDED, PAYMENTS_PENDING,
        or CONFIRMED states.
        """
        booking = BookingService.get_booking_or_404(booking_id)

        # Verify ownership (or admin)
        from apps.accounts.models import UserRole
        if booking.user != user and not user.has_role(UserRole.ADMIN):
            raise ForbiddenException("You do not own this booking.")

        if not BookingStatus.can_transition(booking.status, BookingStatus.CANCELLED):
            raise BookingException(
                f"Cannot cancel a booking in '{booking.status}' status."
            )

        # Release inventory
        with transaction.atomic():
            InventoryService.release_inventory(
                room_id=booking.room_id,
                check_in=booking.check_in_date,
                check_out=booking.checkout_date,
            )
            booking.transition_to(BookingStatus.CANCELLED)

        logger.info("Booking #%d cancelled by user %s.", booking.id, user.email)
        return booking

    @staticmethod
    def confirm_booking(booking_id: int, payment) -> Booking:
        """
        Confirm a booking after successful payment.

        Called by the Stripe webhook handler.
        """
        booking = BookingService.get_booking_or_404(booking_id)

        if not BookingStatus.can_transition(booking.status, BookingStatus.CONFIRMED):
            raise BookingException(
                f"Cannot confirm a booking in '{booking.status}' status."
            )

        booking.payment = payment
        booking.status = BookingStatus.CONFIRMED
        booking.save(update_fields=["payment", "status", "updated_at"])

        logger.info(
            "Booking #%d confirmed. Payment: %s",
            booking.id, payment.transaction_id,
        )

        # Trigger confirmation email (async via Celery)
        from apps.notifications.tasks import send_booking_confirmation_email
        def safe_send_email():
            try:
                send_booking_confirmation_email.delay(booking.id)
            except Exception as e:
                logger.warning("Failed to queue booking confirmation email: %s", str(e))

        transaction.on_commit(safe_send_email)

        return booking

    @staticmethod
    def manual_confirm_booking(
        booking_id: int,
        confirmed_by_user,
        payment_method: str = "CASH",
        notes: str = "",
    ) -> Booking:
        """
        Manually confirm a booking for cash/POS payments.

        Used by lobby staff / hotel managers to bypass Stripe
        when the guest pays at the front desk.

        Args:
            booking_id: The booking to confirm
            confirmed_by_user: The admin/manager performing the action
            payment_method: Payment method (CASH, POS, BANK_TRANSFER)
            notes: Optional notes about the manual confirmation

        Returns:
            Confirmed Booking instance
        """
        import uuid

        booking = BookingService.get_booking_or_404(booking_id)

        # Verify the confirming user has permission (admin or hotel owner)
        from apps.accounts.models import UserRole
        if not confirmed_by_user.has_role(UserRole.ADMIN):
            # Managers can only confirm bookings for their own hotels
            if booking.hotel.owner != confirmed_by_user:
                raise ForbiddenException(
                    "You can only manually confirm bookings for your own hotels."
                )

        # Validate booking state — allow from RESERVED, GUESTS_ADDED, or PAYMENTS_PENDING
        allowed_states = [
            BookingStatus.RESERVED,
            BookingStatus.GUESTS_ADDED,
            BookingStatus.PAYMENTS_PENDING,
        ]
        if booking.status not in allowed_states:
            raise BookingException(
                f"Cannot manually confirm a booking in '{booking.status}' status. "
                f"Allowed states: {', '.join(allowed_states)}."
            )

        # Create a manual payment record
        from apps.payments.models import Payment, PaymentStatus

        manual_txn_id = f"MANUAL-{payment_method}-{uuid.uuid4().hex[:12].upper()}"

        with transaction.atomic():
            payment = Payment.objects.create(
                transaction_id=manual_txn_id,
                price=booking.total_price,
                status=PaymentStatus.CONFIRMED,
            )

            booking.payment = payment
            booking.status = BookingStatus.CONFIRMED
            booking.save(update_fields=["payment", "status", "updated_at"])

        logger.info(
            "Booking #%d manually confirmed by %s (method=%s, txn=%s). Notes: %s",
            booking.id, confirmed_by_user.email, payment_method,
            manual_txn_id, notes or "N/A",
        )

        # Trigger confirmation email (async via Celery)
        from apps.notifications.tasks import send_booking_confirmation_email
        def safe_send_email():
            try:
                send_booking_confirmation_email.delay(booking.id)
            except Exception as e:
                logger.warning("Failed to queue booking confirmation email: %s", str(e))

        transaction.on_commit(safe_send_email)

        return booking

    @staticmethod
    def mark_booking_failed(booking_id: int) -> Booking:
        """Mark a booking as failed and release inventory."""
        booking = BookingService.get_booking_or_404(booking_id)

        with transaction.atomic():
            InventoryService.release_inventory(
                room_id=booking.room_id,
                check_in=booking.check_in_date,
                check_out=booking.checkout_date,
            )
            booking.transition_to(BookingStatus.FAILED)

        logger.warning("Booking #%d marked as FAILED.", booking.id)
        return booking

    @staticmethod
    def expire_stale_reservations() -> int:
        """
        Expire unpaid reservations older than the configured timeout.

        Called periodically by Celery beat.
        Returns the number of expired bookings.
        """
        from django.conf import settings
        from datetime import timedelta

        timeout_minutes = settings.BOOKING_RESERVATION_TIMEOUT_MINUTES
        cutoff = timezone.now() - timedelta(minutes=timeout_minutes)

        stale_bookings = Booking.objects.filter(
            status__in=[BookingStatus.RESERVED, BookingStatus.GUESTS_ADDED],
            created_at__lt=cutoff,
        )

        expired_count = 0
        for booking in stale_bookings:
            try:
                with transaction.atomic():
                    InventoryService.release_inventory(
                        room_id=booking.room_id,
                        check_in=booking.check_in_date,
                        check_out=booking.checkout_date,
                    )
                    booking.status = BookingStatus.EXPIRED
                    booking.save(update_fields=["status", "updated_at"])
                expired_count += 1
                logger.info("Booking #%d expired (stale reservation).", booking.id)
            except Exception as e:
                logger.error("Failed to expire booking #%d: %s", booking.id, str(e))

        return expired_count
