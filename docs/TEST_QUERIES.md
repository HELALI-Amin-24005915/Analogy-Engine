# Test Queries for Report Generation

Use these English prompts to generate reports in **Dual Domain** and **Researcher** modes. Recommended model: **GPT-4o**.

---

## Dual Domain Mode

Paste the **Source** and **Target** texts into the respective fields, then click **Launch Analysis**.

### 1. Hydraulics vs Electricity (classic)

**Source:**
```
In a pipe, high pressure creates a flow of water, but a narrow section restricts it. Valves control the flow; pumps add pressure.
```

**Target:**
```
In a circuit, high voltage drives an electric current, while a resistor limits it. Switches control the flow; batteries provide voltage.
```

---

### 2. Neural networks vs biological cortex

**Source:**
```
Biological neural networks learn through synaptic plasticity (STDP) with precise temporal windows. Neurons integrate inputs and fire spikes; dendrites receive, axons transmit.
```

**Target:**
```
Memristor-based neuromorphic architectures reproduce analog computation and plasticity with ultra-low energy consumption. Crossbar arrays perform vector-matrix multiplication; conductance encodes weights.
```

---

### 3. Blockchain vs medieval ledgers

**Source:**
```
Medieval merchant ledgers and guild systems used witnesses, seals, and communal verification to establish trust. Entries were chained and notarized; disputes were resolved by guild courts.
```

**Target:**
```
Blockchain uses distributed consensus (PoW or PoS), immutable append-only chains, and smart contracts. Miners or validators secure the ledger; nodes replicate and verify transactions.
```

---

### 4. Ecosystems vs microservices

**Source:**
```
Natural ecosystems exhibit resilience through diversity, redundancy, and keystone species. Cascading failures occur when critical nodes collapse; succession and invasion dynamics shape recovery.
```

**Target:**
```
Microservice architectures use circuit breakers, bulkheads, and multi-region deployment. Dependency graphs and blast radius determine failure impact; blue-green and canary releases enable safe rollout.
```

---

## Researcher Mode

Describe your problem or research topic in one or two sentences. The Visionary agent will suggest a source domain, then the full pipeline runs.

### 1. Instant long-range communication

**Problem:**
```
How can we transfer information instantly between two distant points without a physical medium or delay?
```

---

### 2. Fault-tolerant distributed systems

**Problem:**
```
Which principles from natural ecosystems (resilience, redundancy, emergence) can be formally transferred to the design of fault-tolerant, self-organizing distributed systems?
```

---

### 3. Adaptive cyberdefense

**Problem:**
```
How can immune memory mechanisms (clonal selection, adaptive memory) inspire anomaly detection and cyberdefense architectures with continuous learning?
```

---

### 4. Low-power learning hardware

**Problem:**
```
We need ultra-low-power hardware that can learn from streaming data with minimal supervision, like biological brains. What existing domains can we map this to?
```

---

### 5. Trust without central authority

**Problem:**
```
How can we achieve verifiable trust and consensus in a network where no single party is fully trusted?
```

---

## Tips

- **Dual Domain:** Keep source and target to 1–3 sentences each for clearer analogies.
- **Researcher:** Phrase your problem in terms of *concepts*, *goals*, and *constraints* for better suggestions.
- **Filters:** Use "Academic Papers" and "Filter Noise" for more scholarly sources in the report.
