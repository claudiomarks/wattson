# Para evitar prompt de senha, adicione no /etc/sudoers:
echo "$USER ALL=(ALL) NOPASSWD: /usr/bin/tee /sys/class/power_supply/BAT*/charge_control_end_threshold" | sudo tee -a /etc/sudoers
