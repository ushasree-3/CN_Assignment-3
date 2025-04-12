# Distance Vector Routing Simulator

This project implements the **Distance Vector Routing Protocol** using the **Bellman-Ford algorithm**. It simulates message exchanges between nodes in a network to compute optimal paths, including dynamic link cost changes.

## 📁 File Structure

```
.
├── distance_vector.c       # Main driver program
├── node0.c                 # Logic for Node 0
├── node1.c                 # Logic for Node 1
├── node2.c                 # Logic for Node 2
├── node3.c                 # Logic for Node 3
├── output                  # Executable after compilation
├── output_0.txt            # Output file : Link not changed, Trace = 0
├── output_1.txt            # Output file : Link not changed, Trace = 1
├── output_2.txt            # Output file : Link not changed, Trace = 2
├── link_changed_output_0.txt   # Output files with link changes, Trace = 0
├── link_changed_output_1.txt   # Output files with link changes, Trace = 1
├── link_changed_output_2.txt   # Output files with link changes, Trace = 2
```

## How to Run

### Step 1: Compile the Code
```bash
gcc distance_vector.c node0.c node1.c node2.c node3.c -o output
```

### Step 2: Run the Simulator
```bash
./output
```

The program will prompt:
```
Enter trace:
```
Enter a **trace level** (e.g., `2`) and press Enter. The simulation results will then be printed in the terminal.

### Saving Output to Files (Optional)

To save the terminal output to a file manually, use output redirection:

```bash
./output > output_{TRACE}.txt
```

## Enabling Link Cost Change (Advanced)

To simulate **link cost changes** (e.g., from 1 to 20 at time 10000 and back to 1 at 20000):

1. Open `distance_vector.c`.
2. Change the following line:
   ```c
   #define LINKCHANGES 0
   ```
   to
   ```c
   #define LINKCHANGES 1
   ```
3. Recompile the program:
   ```bash
   gcc distance_vector.c node0.c node1.c node2.c node3.c -o output
   ```

4. Run and optionally save output:
   ```bash
   ./output > link_changed_output_{TRACE}.txt
   ```
   
5. The program will prompt:
```
Enter trace:
```
Enter a **trace level** (e.g., `1`) and press Enter. The simulation results will then be printed in the terminal.

## Notes

- The simulator shows how each node's distance table evolves as it receives updates from its neighbors.
- Use different trace levels (`0`, `1`, or `2`) to control the verbosity of the simulation.

