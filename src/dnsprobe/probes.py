"""
DNS probe engine.

Constructs and sends DNS probes (A, B, C) to targets.
Uses dnspython for standard UDP/TCP sockets, no spoofing.
Handles TC bit and TCP fallback.
"""

import random
import string
import hashlib
import dns.message
import dns.name
import dns.rrset
import dns.rdataclass
import dns.rdatatype
from typing import Optional, Tuple
from dataclasses import dataclass
import socket
import time

from .models import ProbeEvidence


@dataclass
class ProbeRequest:
    """Single probe request parameters."""
    probe_name: str  # "A", "B", or "C"
    query_name: str
    query_type: str = "A"
    rd_bit: bool = True  # Recursion desired
    timeout: float = 5.0
    server_ip: str = "127.0.0.1"
    server_port: int = 53


class ProbeGenerator:
    """Generate DNS probe queries."""

    @staticmethod
    def generate_nonce(seed: int, iteration: int) -> str:
        """
        Generate deterministic nonce for ext.lab probes.
        
        Ensures reproducibility with seed while maintaining uniqueness.
        """
        nonce_input = f"{seed}:{iteration}".encode()
        hash_digest = hashlib.sha256(nonce_input).hexdigest()[:12]
        return hash_digest

    @staticmethod
    def construct_query(probe_request: ProbeRequest) -> dns.message.Message:
        """Construct DNS query message."""
        q = dns.message.make_query(
            probe_request.query_name,
            probe_request.query_type,
            rdclass=dns.rdataclass.IN
        )
        # Set RD bit based on probe type
        if probe_request.rd_bit:
            q.flags |= dns.flags.RD
        else:
            q.flags &= ~dns.flags.RD
        return q


class ProbeExecutor:
    """Execute DNS probes against a target."""

    @staticmethod
    def send_probe(
        probe_request: ProbeRequest,
        max_retries: int = 3,
        backoff_base: float = 1.5,
        jitter_fraction: float = 0.1,
    ) -> ProbeEvidence:
        """
        Send a DNS probe and collect evidence.
        
        Attempts UDP first; on TC bit, retries with TCP.
        Implements exponential backoff with jitter.
        """
        query = ProbeGenerator.construct_query(probe_request)
        
        evidence = ProbeEvidence(
            probe_name=probe_request.probe_name,
            query_name=probe_request.query_name,
            query_type=probe_request.query_type,
            rd_bit=probe_request.rd_bit,
        )

        # Retry loop with exponential backoff
        for attempt in range(max_retries):
            try:
                # Calculate backoff
                backoff = (backoff_base ** attempt) if attempt > 0 else 0
                jitter = random.uniform(-backoff * jitter_fraction, backoff * jitter_fraction)
                wait_time = max(0, backoff + jitter)
                if attempt > 0:
                    time.sleep(wait_time)

                # Try UDP
                try:
                    response = ProbeExecutor._send_udp(
                        query,
                        probe_request.server_ip,
                        probe_request.server_port,
                        probe_request.timeout
                    )
                    evidence.latency_ms = time.time() * 1000  # Placeholder
                    evidence.retry_count = attempt

                    # Parse response
                    evidence.rcode = dns.rcode.to_text(response.rcode())
                    evidence.aa_flag = bool(response.flags & dns.flags.AA)
                    evidence.ra_flag = bool(response.flags & dns.flags.RA)
                    
                    # Extract answer section
                    if response.answer:
                        evidence.answer_section = [str(rr) for rr in response.answer]

                    # Check for TC bit (truncated)
                    if response.flags & dns.flags.TC:
                        # Retry with TCP
                        try:
                            response = ProbeExecutor._send_tcp(
                                query,
                                probe_request.server_ip,
                                probe_request.server_port,
                                probe_request.timeout
                            )
                            evidence.rcode = dns.rcode.to_text(response.rcode())
                            evidence.aa_flag = bool(response.flags & dns.flags.AA)
                            evidence.ra_flag = bool(response.flags & dns.flags.RA)
                            if response.answer:
                                evidence.answer_section = [str(rr) for rr in response.answer]
                        except Exception as e:
                            evidence.error_type = f"TCP_FALLBACK_FAILED: {type(e).__name__}"
                            continue

                    return evidence

                except socket.timeout:
                    evidence.error_type = "TIMEOUT"
                    if attempt == max_retries - 1:
                        return evidence
                    continue

            except Exception as e:
                evidence.error_type = type(e).__name__
                if attempt == max_retries - 1:
                    return evidence
                continue

        return evidence

    @staticmethod
    def _send_udp(
        query: dns.message.Message,
        server_ip: str,
        server_port: int,
        timeout: float
    ) -> dns.message.Message:
        """Send query via UDP."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        try:
            sock.sendto(query.to_wire(), (server_ip, server_port))
            response_wire, _ = sock.recvfrom(65535)
            response = dns.message.from_wire(response_wire)
            return response
        finally:
            sock.close()

    @staticmethod
    def _send_tcp(
        query: dns.message.Message,
        server_ip: str,
        server_port: int,
        timeout: float
    ) -> dns.message.Message:
        """Send query via TCP."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            sock.connect((server_ip, server_port))
            query_wire = query.to_wire()
            # TCP requires 2-byte length prefix
            sock.sendall(len(query_wire).to_bytes(2, byteorder='big') + query_wire)
            response_len_bytes = sock.recv(2)
            response_len = int.from_bytes(response_len_bytes, byteorder='big')
            response_wire = b''
            while len(response_wire) < response_len:
                chunk = sock.recv(response_len - len(response_wire))
                if not chunk:
                    break
                response_wire += chunk
            response = dns.message.from_wire(response_wire)
            return response
        finally:
            sock.close()
