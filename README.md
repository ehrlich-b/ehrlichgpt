# EhrlichGPT

## Usage

Copy .env.dist to .env and fill in variables with a valid DISCORD_BOT_TOKEN and OPENAI_API_KEY

### With Poetry

Follow the steps found here https://python-poetry.org/docs/#installation to install poetry on your system.

1. Add the poetry dotenv plugin
    ```
    poetry self add poetry-dotenv-plugin
    ```

2. Verify plugin is installed
    ```
    poetry self show plugins
    ```
    You should see something similar to the following:
    ```
    poetry-dotenv-plugin (0.1.0) A Poetry plugin to automatically load environment variables from .env files
        1 application plugin

        Dependencies
        - poetry (>=1.2.0a1)
        - python-dotenv (>=0.10.0)

    poetry-plugin-export (1.3.0) Poetry plugin to export the dependencies to various formats
        1 application plugin

        Dependencies
        - poetry (>=1.3.0,<2.0.0)
        - poetry-core (>=1.3.0,<2.0.0)
    ```

3. Install project dependencies
    ```
    poetry install
    ```

4. Run program
    ```
    poetry run python main.py
    ```

### With Docker

1. Build the image
    ```
    docker build . -t <imagename>:<tag>
    ```

2. Create a volume to persist conversations
    ```
    docker volume create <some_vol_name>
    ```

3. Run program
    ```
    docker run --env-file .env -v <some_vol_name>:/app/conversations <imagename>:<tag>
    ```
