'use strict';

const { release } = require('./package.json');

module.exports.CHECK_UPDATE = process.env.CHECK_UPDATE ? process.env.CHECK_UPDATE.toLowerCase() === 'true' : true;
module.exports.RELEASE = release;
module.exports.PORT = process.env.PORT || '51821';
module.exports.WEBUI_HOST = process.env.WEBUI_HOST || '0.0.0.0';
module.exports.PASSWORD = process.env.PASSWORD;
module.exports.WG_PATH = process.env.WG_PATH || '/etc/wireguard/';
module.exports.WG_DEVICE = process.env.WG_DEVICE || 'eth0';
module.exports.WG_HOST = process.env.WG_HOST;
module.exports.WG_PORT = process.env.WG_PORT || '51820';
module.exports.WG_MTU = process.env.WG_MTU || '1280';
module.exports.WG_PERSISTENT_KEEPALIVE = process.env.WG_PERSISTENT_KEEPALIVE || '25';
module.exports.WG_DEFAULT_ADDRESS = process.env.WG_DEFAULT_ADDRESS || '10.8.0.x';
module.exports.WG_DEFAULT_DNS = typeof process.env.WG_DEFAULT_DNS === 'string'
  ? process.env.WG_DEFAULT_DNS
  : '1.1.1.1';
module.exports.WG_ALLOWED_IPS = process.env.WG_ALLOWED_IPS || [
  '0.0.0.0/5',
  '8.0.0.0/7',
  '11.0.0.0/8',
  '12.0.0.0/6',
  '16.0.0.0/4',
  '32.0.0.0/3',
  '64.0.0.0/2',
  '128.0.0.0/3',
  '160.0.0.0/5',
  '168.0.0.0/6',
  '172.0.0.0/12',
  '172.32.0.0/11',
  '172.64.0.0/10',
  '172.128.0.0/9',
  '173.0.0.0/8',
  '174.0.0.0/7',
  '176.0.0.0/4',
  '192.0.0.0/9',
  '192.128.0.0/11',
  '192.160.0.0/13',
  '192.169.0.0/16',
  '192.170.0.0/15',
  '192.172.0.0/14',
  '192.176.0.0/12',
  '192.192.0.0/10',
  '193.0.0.0/8',
  '194.0.0.0/7',
  '196.0.0.0/6',
  '200.0.0.0/5',
  '208.0.0.0/4',
  '8.8.8.8/32',
  '1.1.1.1/32',
].join(', ');

module.exports.WG_PRE_UP = process.env.WG_PRE_UP || '';
module.exports.WG_POST_UP = process.env.WG_POST_UP || `
iptables -t nat -A POSTROUTING -s ${module.exports.WG_DEFAULT_ADDRESS.replace('x', '0')}/24 -o ${module.exports.WG_DEVICE} -j MASQUERADE;
iptables -A INPUT -p udp -m udp --dport ${module.exports.WG_PORT} -j ACCEPT;
iptables -A FORWARD -i wg0 -j ACCEPT;
iptables -A FORWARD -o wg0 -j ACCEPT;
`.split('\n').join(' ');

module.exports.WG_PRE_DOWN = process.env.WG_PRE_DOWN || '';
module.exports.WG_POST_DOWN = process.env.WG_POST_DOWN || `
iptables -t nat -D POSTROUTING -s ${module.exports.WG_DEFAULT_ADDRESS.replace('x', '0')}/24 -o ${module.exports.WG_DEVICE} -j MASQUERADE;
iptables -D INPUT -p udp -m udp --dport ${module.exports.WG_PORT} -j ACCEPT;
iptables -D FORWARD -i wg0 -j ACCEPT;
iptables -D FORWARD -o wg0 -j ACCEPT;
`.split('\n').join(' ');
module.exports.LANG = process.env.LANGUAGE || 'en';
module.exports.UI_TRAFFIC_STATS = process.env.UI_TRAFFIC_STATS || 'false';
module.exports.UI_CHART_TYPE = process.env.UI_CHART_TYPE || 0;

module.exports.JC = process.env.JC || 10;
module.exports.JMIN = process.env.JMIN || 64;
module.exports.JMAX = process.env.JMAX || 200;
module.exports.S1 = process.env.S1 || 64;
module.exports.S2 = process.env.S2 || 64;
module.exports.H1 = process.env.H1 || '1000-12999';
module.exports.H2 = process.env.H2 || '13000-24999';
module.exports.H3 = process.env.H3 || '25000-36999';
module.exports.H4 = process.env.H4 || '37000-50000';
module.exports.I1 = process.env.I1 || '<b 0x160301>';
module.exports.I2 = process.env.I2 || '<r 3><b 0x0303><r 32>';
module.exports.I3 = process.env.I3 || '<b 0x00><r 5>';
module.exports.I4 = process.env.I4 || '<r 40>';
module.exports.I5 = process.env.I5 || '<b 0xC0000000><r 8><b 0x04><r 100>';
