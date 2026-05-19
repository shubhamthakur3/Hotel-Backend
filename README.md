# 🏨 Hotel Backend API

A production-grade hotel booking backend system built with Django, featuring dynamic inventory management, dynamic pricing, secure JWT authentication, Stripe payment processing, and concurrency-safe reservations.

---

## 🏗 Architecture

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐
│   Nginx     │────▶│  Gunicorn    │────▶│  Django App    │
│  (Reverse   │     │  (WSGI)      │     │  (DRF APIs)    │
│   Proxy)    │     └──────────────┘     └───────┬────────┘
└─────────────┘                                  │
                                    ┌────────────┼────────────┐
                                    │            │            │
                              ┌─────▼───┐  ┌────▼────┐  ┌────▼────┐
                              │PostgreSQL│  │  Redis  │  │ Stripe  │
                              │   (DB)   │  │(Cache/  │  │  (Pay)  │
                              └──────────┘  │ Broker) │  └─────────┘
                                            └────┬────┘
                                                 │
                                        ┌────────▼────────┐
                                        │  Celery Worker   │
                                        │  + Celery Beat   │
                                        └─────────────────┘
```

### Django Apps

| App | Responsibility |
|-----|---------------|
| `accounts` | JWT auth: signup, login, token refresh, roles |
| `users` | User profile, guest management, my bookings |
| `hotels` | Hotel CRUD (admin) + search/browse (public) |
| `rooms` | Room type management under hotels |
| `inventory` | Per-date inventory with availability tracking |
| `bookings` | Booking lifecycle with state machine |
| `pricing` | Dynamic pricing engine (Strategy Pattern) |
| `payments` | Stripe integration + webhook handling |
| `notifications` | Email notifications via Celery |
| `adminpanel` | Reports and hotel booking management |
| `common` | Shared exceptions, pagination, throttles, middleware |

---

## 🔐 Authentication Flow

```
┌────────┐    POST /auth/signup     ┌─────────┐
│  User  │─────────────────────────▶│  Server  │
│        │◀─── Access Token (body)──│          │
│        │◀─── Refresh Token (cookie)│         │
└────────┘                          └─────────┘

┌────────┐    POST /auth/login      ┌─────────┐
│  User  │─────────────────────────▶│  Server  │
│        │◀─── Access Token (body)──│          │
│        │◀─── Refresh Token (cookie)│         │
└────────┘                          └─────────┘

Access Token: 15 min, in Authorization header
Refresh Token: 7 days, in HttpOnly Secure cookie
Rotation: Enabled with blacklisting
```

### Roles: `GUEST`, `HOTEL_MANAGER`, `ADMIN`

---

## 📊 Booking Lifecycle

```
  RESERVED ──▶ GUESTS_ADDED ──▶ PAYMENTS_PENDING ──▶ CONFIRMED
     │                              │
     ▼                              ▼
  EXPIRED                        FAILED
     │                              
  CANCELLED ◀──────────────────────
```

1. **Reserve** → Lock inventory (pessimistic lock), create booking
2. **Add Guests** → Attach guest details
3. **Payment** → Create Stripe Checkout Session
4. **Confirm** → Stripe webhook confirms payment, booking confirmed
5. **Expire** → Celery task expires unpaid reservations after 15 min

---

## 💰 Dynamic Pricing Engine

Uses the **Strategy Pattern** for modular, extensible pricing:

```
Base Price × Surge Factor × Weekend × Holiday × Occupancy × Urgency = Final Price
```

| Strategy | Multiplier | Trigger |
|----------|-----------|---------|
| Surge | Configurable | Set per inventory day by manager |
| Weekend | 1.20x | Friday/Saturday nights |
| Holiday | Up to 1.50x | Database-configurable date ranges |
| Occupancy | 1.10-1.25x | >60% or >80% booked |
| Urgency | 1.10-1.15x | Same-day or next-day booking |

---

## 🛡 Concurrency Protection

Double-booking prevention uses **pessimistic locking**:

```python
with transaction.atomic():
    rows = Inventory.objects.select_for_update().filter(room_id=room_id, date__in=dates)
    # Validate + reserve
    # Other transactions BLOCK here until this commits
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- PostgreSQL 14+
- Redis 7+

### Local Development

```bash
# Clone and navigate
cd "Hotel backend API"

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env
# Edit .env with your database credentials

# Create database
createdb hotel_db

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Docker

```bash
# Copy env file
cp .env.example .env

# Build and start all services
docker-compose up --build

# Run migrations (in another terminal)
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

### Running Celery (separate terminal)

```bash
# Worker
celery -A config.celery worker -l info

# Beat (scheduler)
celery -A config.celery beat -l info
```

---

## 📡 API Endpoints

### Authentication
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/signup` | Public | Register |
| POST | `/api/auth/login` | Public | Login |
| POST | `/api/auth/refresh` | Cookie | Refresh token |
| POST | `/api/auth/logout` | Cookie | Logout |

### User Profile & Guests
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/users/profile` | Get profile |
| PATCH | `/api/users/profile` | Update profile |
| GET | `/api/users/myBookings` | My bookings |
| GET/POST | `/api/users/guests` | List/Add guests |
| PUT/DELETE | `/api/users/guests/{id}` | Update/Remove |

### Hotel Management (Admin)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/admin/hotels` | Create hotel |
| GET | `/api/admin/hotels` | List my hotels |
| GET/PUT/DELETE | `/api/admin/hotels/{id}` | CRUD |
| PATCH | `/api/admin/hotels/{id}/activate` | Activate |

### Room Management (Admin)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/admin/hotels/{id}/rooms` | Create room |
| GET | `/api/admin/hotels/{id}/rooms` | List rooms |
| GET/PUT/DELETE | `/api/admin/hotels/{id}/rooms/{rid}` | CRUD |

### Inventory (Admin)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/inventory/rooms/{rid}` | View inventory |
| PATCH | `/api/admin/inventory/rooms/{rid}` | Update inventory |

### Hotel Browse (Public)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/hotels/search` | Search hotels |
| GET | `/api/hotels/{id}/info` | Hotel details |

### Bookings
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/bookings/init` | Reserve |
| POST | `/api/bookings/{id}/addGuests` | Add guests |
| POST | `/api/bookings/{id}/payments` | Start payment |
| POST | `/api/bookings/{id}/cancel` | Cancel |
| GET | `/api/bookings/{id}/status` | Check status |

### Admin Reports
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/hotels/{id}/bookings` | Hotel bookings |
| GET | `/api/admin/hotels/{id}/reports` | Reports |

### Webhook
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/webhook/payment` | Stripe webhook |

---

## 🧪 Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=apps --cov-report=term-missing

# Run specific test modules
pytest apps/accounts/tests/ -v
pytest apps/bookings/tests/ -v
pytest apps/pricing/tests/ -v
pytest apps/payments/tests/ -v
```

---

## 🌐 Deployment

### Production Stack
- **Gunicorn** — WSGI server (4 workers, 2 threads)
- **Nginx** — Reverse proxy, static files, security headers
- **PostgreSQL** — Database (Neon / Supabase)
- **Redis** — Cache + Celery broker
- **Celery** — Background worker + beat scheduler

### Deploy on Render / Railway / Fly.io

1. Set environment variables from `.env.example`
2. Set `DJANGO_SETTINGS_MODULE=config.settings.production`
3. Run: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
4. Run migrations: `python manage.py migrate`
5. Start Celery worker separately

---

## 📁 Project Structure

```
hotel_backend/
├── config/               # Django project config
│   ├── settings/         # base.py, development.py, production.py
│   ├── celery.py         # Celery configuration
│   └── urls.py           # Root URL router
├── apps/
│   ├── accounts/         # Auth (User model, JWT, permissions)
│   ├── users/            # Profile, guests
│   ├── hotels/           # Hotel CRUD + search
│   ├── rooms/            # Room management
│   ├── inventory/        # Per-date inventory
│   ├── bookings/         # Booking lifecycle
│   ├── pricing/          # Dynamic pricing engine
│   ├── payments/         # Stripe integration
│   ├── notifications/    # Email tasks
│   ├── adminpanel/       # Reports
│   └── common/           # Shared utilities
├── docker-compose.yml
├── Dockerfile
├── nginx/
├── requirements.txt
└── pytest.ini
```

---

## 📄 License

This project is for educational and demonstration purposes.
