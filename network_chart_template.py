import matplotlib.pyplot as plt
import numpy as np

# Create the network payload impact chart
fig, ax = plt.subplots(figsize=(10, 6))

conditions = ['1/1Hz', '1/10Hz', '10/1Hz', '10/10Hz', '50/1Hz', '50/10Hz', '100/1Hz', '100/100Hz']
x = np.arange(len(conditions))
width = 0.35

# Network times - MODIFY THESE VALUES
bp_network = [25, 25, 25, 25, 25, 25, 25, 25]  # Bulletproofs constant 1.4KB
ckks_network = [100, 110, 150, 200, 375, 475, 675, 875]  # CKKS variable payload

# Payload sizes for CKKS labels - MODIFY THESE LABELS
ckks_payloads = ['0.5MB', '0.5MB', '1.0MB', '1.5MB', '3.0MB', '4.0MB', '6.0MB', '8.0MB']

# Create bars
bars1 = ax.bar(x - width/2, bp_network, width, 
               label='Bulletproofs (1.4KB)', color='blue', alpha=0.7)
bars2 = ax.bar(x + width/2, ckks_network, width,
               label='CKKS (524KB-8MB)', color='red', alpha=0.7)

# Add payload size labels on top of CKKS bars
for i, (bar, payload) in enumerate(zip(bars2, ckks_payloads)):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2, height + 10,
            payload, ha='center', va='bottom', fontsize=9, 
            color='black', fontweight='bold', rotation=45)

# Styling
ax.set_xlabel('Sensors/Frequency Configuration', fontweight='bold')
ax.set_ylabel('Network Time (ms)', fontweight='bold')
ax.set_title('Network Overhead: Payload Size Impact', fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(conditions, rotation=45, ha='right')
ax.legend()
ax.grid(True, alpha=0.3, axis='y')

# Set y-axis limit
ax.set_ylim(0, 900)

plt.tight_layout()
plt.savefig('network_payload_impact_modified.png', dpi=300, bbox_inches='tight')
plt.show()
