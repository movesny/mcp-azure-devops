# MCP Server for Azure DevOps (including on premise server)
This project is based on the https://github.com/Vortiago/mcp-azure-devops/
The Docker image of the MCP server is available at [ghcr.io/movesny/mcp-azure-devops](https://github.com/users/movesny/packages/container/package/mcp-azure-devops)

## Usage
In order to use this MCP server in Visual Studio, create the following `.mcp.json` file in the same folder where your `sln` file is.
```json
{
  "inputs": [
    {
      "type": "promptString",
      "id": "ado_token",
      "description": "Azure DevOps Personal Access Token",
      "password": true
    }
  ],
  "servers": {
    "azure-devops": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-e",
        "AZURE_DEVOPS_ORGANIZATION_URL=HERE_ENTER_YOUR_ADO_URL",
        "-e",
        "AZURE_DEVOPS_PAT",
        "ghcr.io/movesny/mcp-azure-devops"
      ],
      "env": {
        "AZURE_DEVOPS_PAT": "${input:ado_token}"
      }
    }
  }
}
```
Obviously more MCP server can be added. For a list of useful existing servers checkout the [catalogue](https://github.com/modelcontextprotocol/servers).

The token can be created in the ADO by clicking on your profile icon in top right corner, selecting "Security" and clicking on "+ New Token".

Now, when you have the token and your Dockers is running, you can start Visual Studio, open the `sln` file, go to the Copilot Chat, switch to the Agent mode and then click on the Tools icon next to it. Make sure the `azure-devops` tools are checked. The VS will automatically prompt you to enter the ADO token.

Now you can test it by asking for example "Which work items are assigned to me in ADO?".

## Troubleshooting
If the MCP server reports connection errors, this is likely due to the network setup.
Our ADO is hosted at 172.17.xxx.xxx, which is liekly in confliect with your Docker/Rancher setup.

### Docker
If you run `docker network inspect bridge`, you will likely see this:
```json
"IPAM": {
    "Driver": "default",
    "Options": null,
    "Config": [
        {
            "Subnet": "172.17.0.0/16",
            "Gateway": "172.17.0.1"
        }
    ]
}
```
This is clearly a problem because there is a conflict in the IP resolution. To fix this, change the IPAM to a different IP range. This can be done in Docker Desktop for Windows by going to the "Settings" -> "Docker Engine" and adding the following section to the configuration:
```json
  "default-address-pools": [
    {
      "base": "172.100.0.0/16",
      "size": 16
    }
  ]
```
Finally, click "Apply & restart".

### Rancher
In cmdline run:
```cmd
rdctl shell
sudo vi /etc/docker/daemon.json
```
Change the file to:
```json
{  "features": {    "containerd-snapshotter": false  },  "default-address-pools": [    {      "base": "172.100.0.0/16",      "size": 16    }  ]}
```
And save (press shift+zz).
Then run:
```cmd
rdctl shutdown
rdctl start
```
You can verify that the changes were written correctly by running:
```
rdctl shell cat /etc/docker/daemon.json
```
In case there was a syntax error, the file would be overwritten by the default values.
