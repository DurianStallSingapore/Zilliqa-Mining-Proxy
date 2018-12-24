# zilpool

Zilliqa mining pool

A pool proxy between [Zilliqa](https://zilliqa.com/) nodes and GPU miners.

## Installation & Usage

1. Setup [Python3.6+](https://www.python.org/downloads/) and [MongoDB](https://docs.mongodb.com/manual/installation/)
2. Clone zil from Github, setup Python requirements
    ```bash
    git clone https://github.com/jiayaoqijia/Zilliqa-Mining-Proxy
    cd Zilliqa-Mining-Proxy
    sudo python setup.py develop 
    ```

3. Change settings
    ```yaml
    # settings for zilpool
    api_server:
      host: 127.0.0.1
      port: 4202
      path: /api
    
    database:
      uri: "mongodb://127.0.0.1:27017/zil_pool"
      # mongodb://[username:password@]host1[:port1][,host2[:port2],...[,hostN[:portN]]][/[database][?options]]
    ```
    MongoDB url format: https://docs.mongodb.com/manual/reference/connection-string/

4. Run server
    ```bash
    python start.py
    ```
    
