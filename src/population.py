import creature 
import numpy as np

class Population:
    def __init__(self, pop_size, gene_count):
        self.creatures = [creature.Creature(
                          gene_count=gene_count) 
                          for i in range(pop_size)]

    @staticmethod
    def get_fitness_map(fits):
        fitmap = []
        total = 0
        for f in fits:
            total = total + f
            fitmap.append(total)
        return fitmap
    
    @staticmethod
    def select_parent(fitmap):
        if not fitmap:
            return None  # or raise an error

        r = np.random.rand() * fitmap[-1]

        for i in range(len(fitmap)):
            if r <= fitmap[i]:
                return i

        # In case rounding issues or bad data prevent a return
        return len(fitmap) - 1

