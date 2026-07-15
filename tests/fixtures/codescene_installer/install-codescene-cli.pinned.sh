#!/bin/sh

set -e

## BEGIN detect headless install via -y
headless_mode=false
while getopts ":y" opt; do
  case ${opt} in
    y)
      headless_mode=true
      ;;
    \?)
      echo "Invalid option: $OPTARG" 1>&2
      exit 1
      ;;
  esac
done
shift $(expr $OPTIND - 1 )
# END

# Check if curl and unzip are available
if ! command -v curl >/dev/null 2>&1; then
  echo "Error: curl is not installed or not in the PATH."
  exit 1
fi

if ! command -v unzip >/dev/null 2>&1; then
  echo "Error: unzip is not installed or not in the PATH."
  exit 1
fi

# Set the download URL based on the OS
os_name="$(uname)"
arch="amd64"
case "$os_name" in
  Linux)
    os_type="linux"
    (uname -m | grep -E "^(arm64|aarch64)") && arch="aarch64"
    ;;
  Darwin)
    os_type="macos"
    (uname -m | grep -Eq ^arm64) && arch="aarch64"
    ;;
  MINGW*|CYGWIN*)
    os_type="windows"
    ;;
  *)
    echo "Unsupported operating system: $os_name"
    exit 1
    ;;
esac

echo "Detected operating system: $os_name ($os_type)"

# Variables
version="${1:-latest}"
artifact="cs"
url="https://downloads.codescene.io/enterprise/cli/$artifact-$os_type-$arch-$version.zip"
zip_path="/tmp/$artifact.zip"
unzip_path="/tmp/$artifact"
exe_name="cs"

echo "Installing CodeScene $artifact version $version"

# Download the zip file
curl -sS -L -o "$zip_path" "$url"

# Unzip the file
mkdir -p "$unzip_path"
unzip "$zip_path" -d "$unzip_path"

# Detect shell and set destination path
if [ "$os_type" = "macos" ]; then
  shell="$(basename "$(dscl . -read /Users/$(whoami) UserShell | cut -d' ' -f2)")"
else
  shell="$(basename "$(grep "^$(whoami)" /etc/passwd | cut -d: -f7)")"
fi

dest_path="$HOME/.local/bin"

case "$shell" in
  bash)
    if [ "$os_type" = "macos" ]; then
      shell_config="$HOME/.bash_profile"
    else
      shell_config="$HOME/.bashrc"
    fi
    ;;
  zsh)
    shell_config="$HOME/.zshrc"
    ;;
  fish)
    shell_config="$HOME/.config/fish/config.fish"
    ;;
    
  *)
    ;;
esac

if [ -n "$shell_config" ]; then
  echo "Detected shell: $shell"
else
  echo "Unsupported shell: \"$shell\""
fi

# Create destination directory and move the binary
mkdir -p "$dest_path"
mv "$unzip_path/$exe_name" "$dest_path/$exe_name"

# Make the binary executable
chmod +x "$dest_path/$exe_name"

# Clean up the downloaded zip file and extracted folder
rm -f "$zip_path"
rm -rf "$unzip_path"

echo "The '$exe_name' binary has been downloaded, unzipped, made executable and moved to '$dest_path'."

# Add the destination path to the PATH variable, depending on the shell
case "$shell" in
  bash|zsh)
    if ! grep -q "PATH=.*${dest_path}" "$shell_config"; then
      echo "Adding $dest_path to your PATH in $shell_config..."
      if [ "$headless_mode" = false ]; then
        echo "Press enter to continue, or ctrl+c to abort and handle it yourself"
        read REPLY < /dev/tty
      fi
      echo "export PATH=\$PATH:$dest_path" >> "$shell_config"
      echo "Your PATH has been updated, you might need to restart your shell for the changes to take effect."
    else
      echo "$dest_path is already in your PATH in $shell_config"
    fi
    ;;
  fish)
    if ! grep -q "fish_user_paths.*${dest_path}" "$shell_config"; then
      echo "Adding $dest_path to your PATH in $shell_config..."
      if [ "$headless_mode" = false ]; then
        echo "Press enter to continue, or ctrl+c to abort and handle it yourself"
        read REPLY < /dev/tty
      fi
      echo "set -U fish_user_paths \$fish_user_paths $dest_path" >> "$shell_config"
      echo "Your PATH has been updated, you might need to restart your shell for the changes to take effect."
    else
      echo "$dest_path is already in your PATH in $shell_config"
    fi
    ;;
  *)
    echo "Couldn't add $dest_path to your PATH, you will have to handle that yourself!"
  ;;
esac

