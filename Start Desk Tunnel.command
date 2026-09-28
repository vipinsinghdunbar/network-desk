#!/bin/bash
# ---------------------------------------------------------------
#  Network Desk - reachable from anywhere, without uploading it.
#
#  Gives you an https:// address for your phone from anywhere in the
#  world. The desk and your data stay on this Mac; only the page is
#  relayed, and it cannot be indexed or reached without the URL.
#
#  A password is required. The address is public to anyone who has
#  it, and the desk holds message excerpts from real conversations.
#
#  macOS blocks downloaded scripts on first launch. After that a
#  normal double-click works.
# ---------------------------------------------------------------
set -e
cd "$(dirname "$0")"

PORT=8901

if ! command -v cloudflared >/dev/null 2>&1; then
  echo
  echo "  cloudflared is not installed. Install it once with:"
  echo
  echo "    brew install cloudflared"
  echo
  echo "  or download it from github.com/cloudflare/cloudflared/releases"
  echo "  and put it in /usr/local/bin."
  echo
  exit 1
fi

if [ ! -f "site/desk.html" ]; then
  echo
  echo "  No site/desk.html yet. Run 'Refresh Network Desk' first."
  echo
  exit 1
fi

# Stored in a plain text file next to the scripts rather than on the command
# line, so the password does not sit in your shell history. The file is listed
# in .gitignore, same as the token file. Treat it as a secret.
if [ ! -f "desk-password.txt" ]; then
  echo
  echo "  Choose a password for the tunnel. It is asked for once, now."
  echo "  Anything you can type on a phone keyboard, but not a word"
  echo "  someone could guess from the name of this tool."
  echo
  printf "  Password: " && read -rs ND_PASSWORD && echo
  printf '%s\n' "$ND_PASSWORD" > desk-password.txt
  chmod 600 desk-password.txt
  echo
fi

ND_PASSWORD="$(cat desk-password.txt)"
export ND_PASSWORD

if ! nc -z 127.0.0.1 "$PORT" >/dev/null 2>&1; then
  echo "  Starting the desk server..."
  (python3 desk_server.py --port "$PORT" --lan >/dev/null 2>&1 &)
  sleep 3
else
  echo "  Desk server already running on $PORT."
fi

echo "  Opening the tunnel..."
echo
cloudflared tunnel --url "http://localhost:$PORT"
echo
echo "  The tunnel has closed. Your desk is still on this Mac."
