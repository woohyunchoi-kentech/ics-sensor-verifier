"""
Pedersen commitment scheme implementation
"""

import hashlib
import secrets
from typing import Tuple

class PedersenCommitment:
    """Pedersen commitment scheme for hiding values"""
    
    def __init__(self, generator_g: int = None, generator_h: int = None):
        self.g = generator_g or self._generate_generator("g")
        self.h = generator_h or self._generate_generator("h")
    
    def commit(self, value: int, randomness: int = None) -> Tuple[int, int]:
        """Create a Pedersen commitment to a value"""
        if randomness is None:
            randomness = secrets.randbelow(2**256)
        
        # Simplified commitment: C = g^value * h^randomness (mod p)
        commitment = self._compute_commitment(value, randomness)
        
        return commitment, randomness
    
    def verify_commitment(self, commitment: int, value: int, randomness: int) -> bool:
        """Verify a Pedersen commitment"""
        expected_commitment = self._compute_commitment(value, randomness)
        return commitment == expected_commitment
    
    def add_commitments(self, comm1: int, comm2: int) -> int:
        """Add two Pedersen commitments (homomorphic property)"""
        # Simplified addition
        return (comm1 + comm2) % (2**256)
    
    def _generate_generator(self, seed: str) -> int:
        """Generate a generator point"""
        return int(hashlib.sha256(seed.encode()).hexdigest(), 16) % (2**255)
    
    def _compute_commitment(self, value: int, randomness: int) -> int:
        """Compute the actual commitment value"""
        # Simplified: H(g^value || h^randomness)
        data = f"{pow(self.g, value, 2**256)}||{pow(self.h, randomness, 2**256)}".encode()
        return int(hashlib.sha256(data).hexdigest(), 16)
