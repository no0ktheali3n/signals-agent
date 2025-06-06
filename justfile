# Justfile — task runner for uv-powered Python projects

# running 'just' without arguments launches list of just commands using fzf
default:
    @just --summary | fzf | xargs just

# Compile the lockfile from requirements.in
compile:
	uv pip compile requirements.in > requirements.lock.txt

# Sync the environment to match the lockfile exactly
sync:
	uv pip sync requirements.lock.txt

# Upgrade all dependencies and sync
upgrade:
	uv pip compile --upgrade requirements.in > requirements.lock.txt
	uv pip sync requirements.lock.txt

# Set up PowerShell script install for justfile and autovenv
init-install:
	powershell -ExecutionPolicy Bypass -File powershell/install.ps1

# Set up starter project files ()
init-projectfiles:
    powershell -ExecutionPolicy Bypass -File powershell/jumpstarter.ps1

# Set up .env from example (make sure .env.example exists, run init-projectfiles first if not))
init-env:
	cp .env.example .env

# Run PowerShell venv activation (if using PS 5.1 and autoenv.ps1)
activate:
	powershell -Command "Enable-VenvAutoActivate"

# Run the main server demo
run:
	uv pip sync requirements.lock.txt
	python main.py

#run server/agent standalone with stdio transport (default)
run-server:
	uv pip sync requirements.lock.txt
	python main.py server

run-agent:
	uv pip sync requirements.lock.txt
	python main.py agent

#run server/agent with http transport
run-server-http:
	uv pip sync requirements.lock.txt
	python server/server.py --transport http

run-agent-http:
	uv pip sync requirements.lock.txt
	python agent/signal_agent.py --transport http

run-inspector:
	npx @modelcontextprotocol/inspector uv run python server/server.py

venv:
	.venv/Scripts/activate

