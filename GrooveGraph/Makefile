.PHONY: up down logs test test-integration seed smoke migrate

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

test:
	docker compose run --rm --no-deps api pytest -m "not integration and not e2e and not requires_docker"
	docker compose run --rm --no-deps web npm test

test-integration:
	docker compose up -d --build
	docker compose exec -T api alembic upgrade head
	docker compose run --rm api pytest -m "integration or e2e or requires_docker"

seed:
	docker compose run --rm --no-deps api python -m app.seed

migrate:
	docker compose run --rm api alembic upgrade head

smoke:
	docker compose up -d --build
	docker compose exec -T api python -c "import json, urllib.request; data=json.load(urllib.request.urlopen('http://localhost:8000/health', timeout=5)); assert data['status'] == 'ok'; print('api health ok')"
	docker compose exec -T web node -e "fetch('http://localhost:3000').then(r => { if (!r.ok) throw new Error('web health failed: ' + r.status); console.log('web health ok') })"
