# Automatic checkout updates

Burito can periodically fetch `origin/main` and fast-forward the checkout at
`~/Burito`. Install the per-user timer from Konsole:

```sh
cd ~/Burito
bash scripts/install-auto-update.sh
```

It checks every 15 minutes after a short startup delay. The service only
updates a clean `main` branch tracking `origin/main` from this Burito GitHub
repository. It never resets, stashes, commits, pushes, or installs software.
If there are local changes, an active Eve runtime, a divergent branch, a
network error, or changed dependency manifests, it defers or fails safely.
Deferred checks retry on the next timer run. Dependency changes require manual
review and setup.

An update changes the checkout only; it does not restart an open Burito chat
or install packages. New code is used on the next launch. Check timer and recent
service output with:

```sh
systemctl --user status burito-auto-update.timer
journalctl --user -u burito-auto-update.service -n 30 --no-pager
```

Disable automatic checks with:

```sh
systemctl --user disable --now burito-auto-update.timer
```
