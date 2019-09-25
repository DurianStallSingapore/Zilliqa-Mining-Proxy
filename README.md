# Zilliqa Mining Proxy

A mining proxy between [Zilliqa](https://zilliqa.com/) CPU nodes and GPU mining rigs. This proxy only runs on a machine with a public IP address. The public IP address is required for both the Zilliqa CPU nodes and GPU mining rigs to connect to it.

## Setup architecture

The setup architecture is illustrated in the image shown below. All communications amongst these three parties are via the JSON-RPC protocol.

![Setup-architecture](https://i.imgur.com/hJZexcb.jpg)

* The CPUs in the CPU cluster will be running the [**Zilliqa clients**](https://github.com/Zilliqa/Zilliqa) to process transactions and carry out the pBFT consensus to receive rewards.
* The GPU rigs in the GPU cluster will run the [**Zilminer**](https://github.com/DurianStallSingapore/ZILMiner/) software to do the PoW process and provide PoW solutions to CPU cluster via the Mining proxy server.
* The Mining proxy server will process the mining request from the CPU cluster and handle the Mining Register/Response from the GPU cluster.


## Installation & Usage

1. Install [Python3.7.2+](https://www.python.org/downloads/) and [MongoDB](https://docs.mongodb.com/manual/installation/)

2. Clone Zilliqa-Mining-Proxy, and setup the Python dependencies:
    ```bash
    git clone https://github.com/DurianStallSingapore/Zilliqa-Mining-Proxy
    cd Zilliqa-Mining-Proxy
    sudo python3.7 setup.py develop
    ```

3. Change the settings in the `pool.conf` file for the following:
    ```yaml
    # settings to change for zilpool
    api_server:
      host: 127.0.0.1 # key in your machine's internal/private IP
      port: 4202 # key in the port you are using for CPU nodes' Zilliqa clients
      path: /api # key in the path for connecting to zilpool
    
    database:
      uri: "mongodb://127.0.0.1:27017/zil_pool"
      # For more details, refer to: https://docs.mongodb.com/manual/reference/connection-string/
    ```

4. Find out the public IP address of this machine:
    ```bash
    curl https://ipinfo.io/ip
    ```
    You will be required to connect the Zilliqa CPU nodes running the **Zilliqa Clients** and the mining rigs running **Zilminers** to this proxy server's public IP address.
    * For the Zilliqa CPU nodes, you have to edit the `constants.xml` file `REMOTE_MINE` and `MINING_PROXY_URL` parameter:
        ```yaml
        <REMOTE_MINE>true</REMOTE_MINE>
        <MINING_PROXY_URL>http://52.220.146.17:4202/api</MINING_PROXY_URL>
    * For the GPU mining rigs, you have to change the input `proxy_ip` to this public IP address when setting up the Zilminers.
        
5. Run Zilliqa proxy server
    ```bash
    python3.7 start.py
    ```
