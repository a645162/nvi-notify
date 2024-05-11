#!/usr/bin/env bash

## 开放端口
sudo iptables -I INPUT -p tcp --dport 8080 -j ACCEPT
## 端口重定向
sudo iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 8080
sudo ip6tables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 8080
