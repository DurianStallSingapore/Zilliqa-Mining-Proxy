# Zilliqa Mining Proxy

A mining proxy between [Zilliqa](https://zilliqa.com/) CPU nodes and GPU mining rigs. This proxy is required to run on a machine with a public IP address, in order for the Zilliqa CPU nodes and GPU mining rigs to connect to it.

## Installation & Usage

1. Install [Python3.6+](https://www.python.org/downloads/) and [MongoDB](https://docs.mongodb.com/manual/installation/)

2. Clone Zilliqa-Mining-Proxy, and setup the Python dependencies:
    ```bash
    git clone https://github.com/DurianStallSingapore/Zilliqa-Mining-Proxy
    cd Zilliqa-Mining-Proxy
    sudo python setup.py develop
    ```

3. Change the settings in the `pool.conf` file for the following:
    ```yaml
    # settings to change for zilpool
    api_server:
      host: 127.0.0.1 # key in your machine's internal/private IP
      port: 4202 # key in the port you are using for Zilliqa client
      path: /api # key in the path for connecting to zilpool
    
    database:
      uri: "mongodb://127.0.0.1:27017/zil_pool"
      # For more details, refer to: https://docs.mongodb.com/manual/reference/connection-string/
    ```

4. Find out the public IP address of this machine:
    ```bash
    curl https://ipinfo.io/ip
    ```
    You will be required to connect the Zilliqa CPU nodes and the mining rigs to your public IP address.
    * For Zilliqa CPU nodes, you have to edit the `constants.xml` file `MINING_PROXY_URL` parameter:
        ```yaml
        <MINING_PROXY_URL>http://52.220.146.17:4202/api</MINING_PROXY_URL>
    * For the GPU mining rigs, you have to change the input `proxy_ip` to that of your public IP address.
        ```
        
5. Run Zilliqa proxy server
    ```bash
    python start.py
    ```
