# Data-Comm-Project

# Simple P2P File Sharing System

A lightweight peer-to-peer (P2P) file sharing system built in Python using sockets and multithreading. The system consists of a central tracker for peer discovery and multiple peers that can share, search, and download files directly from each other.

---

## Features

- Central tracker for peer discovery
- Peer-to-peer file transfer (no central file server)
- Chunked file transfer for large files
- Multithreaded downloads for speed
- File integrity verification using SHA-256 hashing
- Basic peer messaging (echo, ping, search, download)


## How It Works

### 1. Tracker
- Peers register themselves with the tracker.
- Tracker maintains a list of active peers.
- Peers request the peer list from the tracker when searching for files.

### 2. Peer Node
Each peer:
- Runs a server to accept incoming requests.
- Connects to other peers to:
  - Search for files
  - Request file metadata
  - Download file chunks

### 3. File Download Process
1. Peer requests file info (`FILE_INFO`)
2. Peer receives:
   - number of chunks
   - SHA-256 hash
3. Peer downloads chunks concurrently using threads
4. File is reassembled locally
5. Integrity is verified using hash comparison

---

## Setup Instructions

### 1. Start the Tracker


#python tracker.py
#Default: 127.0.0.1
#Port: 9000

### 2. Start Peers

Run multiple peers in separate terminals:
    python peer.py <port>

Each peer will automatically:

Create a shared folder: shared_<port>/
Register with the tracker

### Peer Commands

Ping another peer:
    ping <ip> <port>

Send messages to another peer:
    echo <ip> <port> <message>

Search the network for a file:
    search <filename>

Connect to a port:
    connect <ip> <port>

Download a file:
    download <filename> <peer_ip> <peer_port>

### File Sharing

Each peer stores files in their own folders:
    shared_<port>/
Only files in this directory are discoverable and shareable.

### Message Protocol

All communication uses JSON messages
Ex:
{
  "type": "SEARCH",
  "filename": "example.txt"
}

### Notes

Uses TCP sockets for reliability
Uses multithreading for:
    concurrent peer handling
    parallel chunk downloads
File integrity ensured via SHA-256 hashing
Simple tracker (no persistence or authentication)


