import base64
import json
from datetime import datetime, timedelta

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import requests
from flask import Flask

def decrypt(e):
    def generate_key(date: datetime):
        # https://stackoverflow.com/a/2267428
        def baseN(num,b,numerals="0123456789abcdefghijklmnopqrstuvwxyz"):
            return ((num == 0) and numerals[0]) or (baseN(num // b, b, numerals).lstrip(numerals[0]) + numerals[num % b])
        # timezone_offset = date.utcoffset().total_seconds() if date.utcoffset() else 0
        timezone_offset = -120
        adjusted_date = date + timedelta(minutes=timezone_offset)
        day = adjusted_date.day
        reversed_day = int(str(day).zfill(2)[::-1])
        year = adjusted_date.year
        reversed_year = int(str(year)[::-1])

        # Create the key
        key_part = baseN(int(str(int(date.timestamp() * 1000)), 16), 36)  # Interpret timestamp as hex
        key_part += baseN((year + reversed_year) * (day + reversed_day), 24)

        # Ensure the key is 14 characters long
        if len(key_part) < 14:
            key_part = key_part.ljust(14, '0')
        elif len(key_part) > 14:
            key_part = key_part[:14]

        return '#' + key_part + '$'

    # Assuming e is a dictionary with 'lastModified' and 'response' keys
    last_modified_date = datetime.fromtimestamp(e['lastModified'] / 1000)  # Convert from milliseconds
    key = generate_key(last_modified_date)

    # Prepare the key and IV
    key_bytes = key.encode('utf-8')
    iv = key.upper().encode('utf-8')

    # Decrypt the response
    cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
    decrypted_data = unpad(cipher.decrypt(base64.b64decode(e['response'])), AES.block_size)

    return json.loads(decrypted_data.decode('utf-8'))

def get_speed():
    e = requests.get("https://itp-rg-sls.infosys-platforms.com/prod/api/match-beats/data/year/2025/eventId/520/matchId/SM001").json()
    decrypted_data = decrypt(e)
    lastPoint = decrypted_data["setData"][-1]["gameData"][-1]["pointData"][-1]
    return [lastPoint["faultSrvSpd"], lastPoint["serveSpeed"], lastPoint["tm1Rally"] + lastPoint["tm2Rally"]]

app = Flask(__name__)

@app.route("/s")
def speed():
    return get_speed()

@app.route("/")
def home():
    return """\
<script>
window.addEventListener("DOMContentLoaded", async function() {
    var oldSpeed;
    async function u() {
        var [faultSpeed, speed, lg] = await (await fetch("/s")).json();
        fs.textContent = faultSpeed ? faultSpeed + ' km/h (1er s)' : '';
        s.textContent = speed + ' km/h' + (faultSpeed ? ' (2e s)' : '');
        if(oldSpeed != speed) {
            l.textContent = '...';
            setTimeout(() => l.textContent = lg + ' coups', 10000);
        }
        oldSpeed = speed;
    }
    setInterval(u, 2000);
    await u();
});
</script>
<style>body {margin: 0; min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; font-family: Montserrat; font-size: 10em}</style>
<div id="fs"></div>
<div id="s"></div>
<div id="l"></div>
"""

if __name__ == "__main__":
    app.run(debug=True)
