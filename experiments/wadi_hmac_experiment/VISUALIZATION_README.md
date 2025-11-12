# WADI HMAC Experiment Visualization Documentation

## 📊 **Overview**

This document describes the comprehensive visualization suite for the WADI HMAC-SHA256 experiment results, providing both Korean and English versions of all charts and analyses.

## 🎯 **Experiment Summary**

- **Total Conditions**: 16 (4 sensor counts × 4 frequencies)
- **Total Requests**: 16,000 
- **Success Rate**: 100% 
- **Verification Rate**: 100%
- **Experiment Duration**: 31 minutes
- **Server**: 192.168.0.11:8085/api/v1/verify/hmac

## 📈 **Visualization Files**

### **English Version (Recommended for International Use)**
Location: `../results/hmac_visualizations_english/`

1. **01_time_breakdown_analysis_en.png**
   - **Purpose**: Processing time breakdown analysis
   - **Chart Type**: Stacked bar chart
   - **Shows**: Encryption, Network, Decryption, and Verification times
   - **Key Insight**: Network transmission dominates 99.1% of total processing time

2. **02_rps_performance_en.png**  
   - **Purpose**: RPS (Requests Per Second) performance analysis
   - **Chart Type**: Bar chart + Line chart
   - **Shows**: Maximum RPS by sensor count & Average RPS trend by frequency
   - **Key Insight**: Peak performance of 3,170 RPS at 100 sensors × 100Hz

3. **03_scalability_heatmap_en.png**
   - **Purpose**: Scalability analysis across sensor counts and frequencies
   - **Chart Type**: Heatmap matrix
   - **Shows**: RPS values color-coded by performance level
   - **Key Insight**: Linear scalability with sensor count and frequency

4. **04_efficiency_analysis_en.png**
   - **Purpose**: System efficiency breakdown
   - **Chart Type**: Dual pie charts
   - **Shows**: Time composition percentages & Verification success rate
   - **Key Insight**: 100% verification success across all 16 conditions

5. **05_comprehensive_dashboard_en.png** ⭐
   - **Purpose**: Complete experiment overview dashboard
   - **Chart Type**: Multi-panel dashboard (6 sub-charts)
   - **Shows**: All metrics in one comprehensive view
   - **Key Insight**: Complete performance profile at a glance

### **Korean Version (Original)**
Location: `../results/hmac_visualizations/`
- Same chart types with Korean labels and text
- Files follow same naming pattern without "_en" suffix

## 📊 **Key Performance Metrics Visualized**

### **Time Analysis**
- **Encryption Time**: 0.032ms average (HMAC-SHA256 generation)
- **Network Time**: 27.7ms average (RTT to server)
- **Decryption Time**: 0.02ms average (message parsing)
- **Verification Time**: 0.15ms average (server-side HMAC verification)
- **Total Time**: 27.89ms average

### **Scalability Metrics**
- **Sensor Scaling**: 1 → 10 → 50 → 100 sensors
- **Frequency Scaling**: 1Hz → 2Hz → 10Hz → 100Hz
- **RPS Range**: 1.0 to 3,170.1 requests per second
- **Linear Scalability**: Consistent per-request latency

### **System Efficiency**
- **CPU Efficiency**: HMAC operations use <1% of total time
- **Network Dependency**: 99.1% of latency from network RTT
- **Memory Efficiency**: Symmetric key cryptography minimizes memory usage
- **Throughput**: Maximum 3,170 concurrent requests per second

## 🎨 **Chart Specifications**

### **Visual Design**
- **Resolution**: 300 DPI high-quality PNG format
- **Color Scheme**: Professional color palette (#FF6B6B, #4ECDC4, #45B7D1, #96CEB4)
- **Typography**: Clear, readable fonts optimized for presentations
- **Layout**: Responsive design suitable for reports and presentations

### **Data Accuracy**
- **Source**: Direct extraction from FINAL_WADI_HMAC.md experimental results
- **Validation**: All 16 conditions with 1,000 requests each accurately represented
- **Consistency**: Cross-validated across all visualization types

## 📋 **Usage Recommendations**

### **For Academic Papers**
- Use **05_comprehensive_dashboard_en.png** for complete overview
- Use **01_time_breakdown_analysis_en.png** for latency analysis
- Use **03_scalability_heatmap_en.png** for scalability discussion

### **For Technical Presentations**
- Start with **05_comprehensive_dashboard_en.png** for summary
- Drill down with **02_rps_performance_en.png** for throughput analysis
- Use **04_efficiency_analysis_en.png** for efficiency insights

### **For Documentation**
- Include all 5 charts for comprehensive coverage
- Reference specific metrics from dashboard summary
- Highlight 100% success rate achievement

## 🔧 **Technical Details**

### **Data Processing**
- **Framework**: Python matplotlib + seaborn
- **Data Source**: 16 experimental conditions with actual measured values
- **Calculations**: Statistical aggregations (mean, max, percentages)
- **Validation**: Cross-checked against original experiment logs

### **File Formats**
- **Primary**: PNG (300 DPI, high quality)
- **Compatibility**: Suitable for LaTeX, Word, PowerPoint, web display
- **Size**: Optimized for quality vs file size balance

## 🏆 **Key Findings Highlighted**

1. **Perfect Security**: 100% HMAC verification success across 16,000 requests
2. **Excellent Scalability**: Linear performance scaling from 1 to 100 sensors
3. **Real-time Capability**: 100Hz (10ms interval) high-frequency processing
4. **Network-Limited**: System performance constrained by network latency, not crypto
5. **Efficiency**: HMAC processing represents <1% of total response time

---

**Generated**: September 1, 2025  
**Experiment Date**: August 29, 2025  
**Total Visualization Files**: 10 (5 English + 5 Korean)