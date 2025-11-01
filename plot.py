import numpy as np
import matplotlib.pyplot as plt

# Example: generate a random IQ signal
N = 1000
I = np.random.randn(N)  # In-phase samples
Q = np.random.randn(N)  # Quadrature samples

# Scatter plot of I vs Q
plt.figure(figsize=(6,6))
plt.scatter(I, Q, s=5, alpha=0.6)
plt.title("IQ Constellation Plot")
plt.xlabel("In-phase (I)")
plt.ylabel("Quadrature (Q)")
plt.grid(True)
plt.axis('equal')  # Equal scaling for both axes
plt.show()

