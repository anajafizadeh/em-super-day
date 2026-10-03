# Backend solution (Django)

Python 3.14, Django 5.2 LTS.

## Setup

```sh
cd backend/solution
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env.local   # then set DJANGO_SECRET_KEY
```

The app fails fast with `ImproperlyConfigured` if a required variable is missing.

## Run

```sh
node backend/mock-crm.mjs          # from the repo root, in another terminal
python manage.py runserver 3000
```

## Layout

- `config/`: project settings and root URLconf
- `portfolio/`: the portfolio app; its routes are in `portfolio/urls.py`, mounted at `/`
- `constants.py`: shared non-secret constants from the spec
