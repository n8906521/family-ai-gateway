def get_available_memory():
    """
    Reads /proc/meminfo to calculate available memory in GB.
    Follows the 3-step plan: Initialization, Extraction/Calculation, and Formatting.
    """
    try:
        # Step 1: Module Initialization (using built-in open for /proc/meminfo)
        with open('/proc/meminfo', 'r') as f:
            lines = f.readlines()

        available_kb = 0
        for line in lines:
            # Step 2: Data Extraction
            # MemAvailable is the most accurate metric for "free" memory in modern Linux
            if line.startswith('MemAvailable:'):
                parts = line.split()
                available_kb = int(parts[1])
                break

        # Step 2 (cont.): Calculation
        # Convert KB to GB (1024^2)
        available_gb = available_kb / (1024**2)

        # Step 3: Formatting and Console Output
        print(f"Available Memory: {available_gb:.2f} GB")

    except FileNotFoundError:
        print("Error: /proc/meminfo not found. This script is intended for Linux systems.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    get_available_memory()