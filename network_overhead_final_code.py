import matplotlib.pyplot as plt
import numpy as np

# Create visualization with correct Y-axis range
fig, ax = plt.subplots(figsize=(12, 8))

conditions = ['1/1Hz', '1/2Hz', '1/10Hz', '10/1Hz', '10/2Hz', '10/10Hz']
x = np.arange(len(conditions))
width = 0.35

# Common conditions only - actual measured values
bp_network_actual = [15.3, 16.2, 18.7, 41.5, 42.8, 88.2]  # From HAI Bulletproofs results
ckks_network_actual = [110, 115, 125, 180, 190, 250]  # From HAI CKKS results

# CKKS payloads for labels (based on actual HAI CKKS experiments)
ckks_payloads = [524, 524, 524, 1024, 1024, 1536]  # KB

# Create bars
bars1 = ax.bar(x - width/2, bp_network_actual, width, 
               label='Bulletproofs (1.4KB)', color='#2E86AB', alpha=0.8)
bars2 = ax.bar(x + width/2, ckks_network_actual, width, 
               label='CKKS (Variable)', color='#A23B72', alpha=0.8)

# Add payload size annotations
for i in range(len(conditions)):
    # Bulletproofs annotation (constant 1.4KB)
    ax.text(i - width/2, bp_network_actual[i] + 10, 
            '1.4KB', ha='center', fontsize=9, color='#2E86AB', fontweight='bold')
    
    # CKKS annotation (variable)
    if ckks_payloads[i] >= 1024:
        payload_text = f'{ckks_payloads[i]/1024:.1f}MB'
    else:
        payload_text = f'{ckks_payloads[i]}KB'
    ax.text(i + width/2, ckks_network_actual[i] + 10, 
            payload_text, ha='center', fontsize=9, color='#A23B72', fontweight='bold')

# Add load impact arrows for common conditions
ax.annotate('Load impact', xy=(3, bp_network_actual[3]), xytext=(3, 25),
            arrowprops=dict(arrowstyle='->', color='red', lw=2),
            fontsize=10, ha='center', color='red', fontweight='bold')

ax.annotate('Load + Payload', xy=(5, ckks_network_actual[5]), xytext=(5, 200),
            arrowprops=dict(arrowstyle='->', color='red', lw=2),
            fontsize=10, ha='center', color='red', fontweight='bold')

# Styling
ax.set_xlabel('Sensors/Frequency Configuration', fontsize=12, fontweight='bold')
ax.set_ylabel('Network Time (ms)', fontsize=12, fontweight='bold')

ax.set_xticks(x)
ax.set_xticklabels(conditions, rotation=45, ha='right')
ax.grid(True, alpha=0.3, axis='y')
ax.legend(loc='upper right', fontsize=11)

# Add baseline reference line
ax.axhline(y=25, color='gray', linestyle='--', alpha=0.7, linewidth=2)
ax.text(4.5, 28, 'Baseline RTT (~25ms)', ha='center', fontsize=10,
        color='black', fontweight='bold',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

# Set Y-axis range to properly fit all data with margin
max_value = max(max(bp_network_actual), max(ckks_network_actual))
ax.set_ylim(0, max_value + 50)  # 250 + 50 = 300ms max

# Move summary statistics box
stats_text = '''Key Observations (Common Conditions):
• Bulletproofs: 15.3ms → 88.2ms (5.8× increase under load)
• CKKS: 110ms → 250ms (payload + load effects)
• Load impact significant at 10 sensors
• CKKS consistently higher due to payload size'''

ax.text(0.02, 0.65, stats_text, transform=ax.transAxes, 
        fontsize=10, verticalalignment='top',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.9))

plt.tight_layout()
plt.savefig('network_overhead_common_conditions.png', dpi=300, bbox_inches='tight')
plt.show()
