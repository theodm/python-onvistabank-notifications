from fabric import Connection


# Liest die secrets.properties Datei und gibt ein ConfigParser-Objekt zurück.
def read_secrets():
    config = configparser.ConfigParser()
    config.read("secrets.properties")
    return config


secrets = read_secrets()

# Define the remote host, username, and password
remote_host = secrets.get("DEPLOY_REMOTE_HOST")
remote_user = secrets.get("DEPLOY_REMOTE_USER")
remote_pass = secrets.get("DEPLOY_REMOTE_PASSWORD")

# Upload the entire project folder to the remote machine
local_path = "."
remote_path = "/home/pi/python-onvistabank-notifications"

# Create a Fabric connection to the remote host
c = Connection(
    host=remote_host, user=remote_user, connect_kwargs={"password": remote_pass}
)

# Copy the project folder to the remote machine
c.put(local_path, remote_path, recursive=True)

# Install Python and Pipenv if they are not already installed
c.sudo("apt-get update && apt-get install -y python3 python3-pip")
c.run("pip3 install pipenv")

# Install the project dependencies with Pipenv
c.run(f"cd {remote_path} && pipenv install")

# Copy the service file to the remote machine
c.put("./deploy/python-onvistabank-notifications.service", "/etc/systemd/system/")

# Start the service
c.sudo("systemctl daemon-reload")
c.sudo("systemctl enable python-onvistabank-notifications")
c.sudo("systemctl start python-onvistabank-notifications")
