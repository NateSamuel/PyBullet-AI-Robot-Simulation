import unittest
import population
import simulation 
import genome 
import creature 
import numpy as np
import csv
import os

class TestGA(unittest.TestCase):
    def testBasicGA(self):
        initial_pop_size = 1000   # large initial population
        final_pop_size = 200     # smaller population after gen 0
        pop = population.Population(pop_size=initial_pop_size, gene_count=5)

        sim = simulation.ThreadedSim(pool_size=8)
        log_file = "fitness_log.csv"
        with open(log_file, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Generation", "MaxFit"])
        log_file_2 = "fitness_log_info.csv"
        write_header = not os.path.exists(log_file_2)

        with open(log_file_2, mode='a', newline='') as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(["iteration", "fittest", "mean_fitness", "weakest", "mean_links", "max_links", "min_links"])
        for iteration in range(2000):
            sim.eval_population(pop, 3000)

            fits = []
            for cr in pop.creatures:
                d = cr.get_distance_to_peak()
                base_fitness = 1 / (d + 1e-6)
                
                tiny_penalty, tiny_joints, tiny_muscles = cr.check_tiny_parts()
                large_penalty, large_joints, large_muscles = cr.check_large_parts()
                simple_penalty, joint_count, muscle_count = cr.check_too_simple()

                adjusted_fitness = base_fitness + tiny_penalty + large_penalty + simple_penalty
                fits.append(adjusted_fitness)
                
                if tiny_penalty < 0 or simple_penalty < 0:
                    print(f"Creature penalties: tiny={tiny_penalty},large={large_penalty}, simple={simple_penalty} | joints={joint_count}, muscles={muscle_count}")

            links = [len(cr.get_expanded_links()) for cr in pop.creatures]
            with open(log_file_2, mode='a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    iteration,
                    round(np.max(fits), 3),
                    round(np.mean(fits), 3),
                    round(np.min(fits), 3),
                    round(np.mean(links), 3),
                    round(np.max(links), 3),
                    round(np.min(links), 3)
                ])
            print(iteration, "fittest:", np.round(np.max(fits), 3), 
                  "mean:", np.round(np.mean(fits), 3), 
                  "mean links", np.round(np.mean(links)), 
                  "max links", np.round(np.max(links)))       

            max_fit = np.round(np.max(fits), 5)
            with open(log_file, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([iteration, max_fit])

            # Population size control
            if iteration == 0:
                current_pop_size = initial_pop_size
            else:
                current_pop_size = final_pop_size

            fit_map = population.Population.get_fitness_map(fits)
            new_creatures = []

            for i in range(current_pop_size):
                p1_ind = population.Population.select_parent(fit_map)
                p2_ind = population.Population.select_parent(fit_map)
                p1 = pop.creatures[p1_ind]
                p2 = pop.creatures[p2_ind]
                dna = genome.Genome.crossover(p1.dna, p2.dna)
                dna = genome.Genome.point_mutate(dna, rate=0.3, amount=0.3)
                dna = genome.Genome.shrink_mutate(dna, rate=0.2)
                dna = genome.Genome.grow_mutate(dna, rate=0.3)
                cr = creature.Creature(1)
                cr.update_dna(dna)
                new_creatures.append(cr)

            # Elitism: preserve best individual
            max_index = np.argmax(fits)
            elite_cr = pop.creatures[max_index]
            new_cr = creature.Creature(1)
            new_cr.update_dna(elite_cr.dna)
            if new_creatures:
                new_creatures[0] = new_cr

            filename = "elite_" + str(iteration) + ".csv"
            genome.Genome.to_csv(elite_cr.dna, filename)

            # Update population
            pop.creatures = new_creatures

        self.assertNotEqual(fits[0], 0)

if __name__ == "__main__":
    unittest.main()