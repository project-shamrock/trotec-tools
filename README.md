# trotec-tunnel

A tunneling service that exposes a Trotec Ruby laser (connected to a remote Windows host) over the network via a Node.js service.

## Overview

The Trotec Ruby laser is driven by software on a Windows machine. This project provides a Node service running on that Windows host that accepts jobs over a tunnel, translating them into commands the laser software understands. This lets other systems on the network submit laser jobs without direct access to the Windows machine.

## Architecture

```
[ Client ] ---> [ Tunnel ] ---> [ Node Service (Windows Host) ] ---> [ Trotec Ruby Laser ]
```

## Getting Started

```bash
npm install
```

## License

Private - project-shamrock
