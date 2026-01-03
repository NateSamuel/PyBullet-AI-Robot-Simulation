import genome 
from xml.dom.minidom import getDOMImplementation
from enum import Enum
import numpy as np

class MotorType(Enum):
    PULSE = 1
    SINE = 2

class Motor:
    def __init__(self, control_waveform, control_amp, control_freq):
        if control_waveform <= 0.5:
            self.motor_type = MotorType.PULSE
        else:
            self.motor_type = MotorType.SINE
        self.amp = max(0.1, min(control_amp, 1.0))
        self.freq = max(0.05, min(control_freq, 0.5))
        self.phase = 0
    

    def get_output(self):
        self.phase = (self.phase + self.freq) % (np.pi * 2)

        if self.motor_type == MotorType.PULSE:
            output = self.amp if self.phase < np.pi else -self.amp

        elif self.motor_type == MotorType.SINE:
            output = self.amp * np.sin(self.phase)

        return output

class Creature:
    MIN_JOINT_RADIUS = 0.06
    MIN_MUSCLE_LENGTH = 0.1
    TINY_PART_PENALTY = -10
    MAX_JOINT_RADIUS = 0.7
    MAX_MUSCLE_LENGTH = 3.0
    LARGE_PART_PENALTY = 5
    MIN_JOINT_COUNT = 6
    MIN_MUSCLE_COUNT = 6

    SIMPLE_CREATURE_PENALTY = -20
    def __init__(self, gene_count, peak_pos=None):
        self.spec = genome.Genome.get_gene_spec()
        self.dna = genome.Genome.get_random_genome(len(self.spec), gene_count)
        self.flat_links = None
        self.exp_links = None
        self.motors = None
        self.start_position = None
        self.last_position = None
        self.peak_pos = peak_pos


    def get_flat_links(self):
        if self.flat_links == None:
            gdicts = genome.Genome.get_genome_dicts(self.dna, self.spec)
            self.flat_links = genome.Genome.genome_to_links(gdicts)
        return self.flat_links
    
    def get_expanded_links(self):
        self.get_flat_links()
        
        if self.flat_links is None or len(self.flat_links) == 0:
            raise ValueError("Invalid genome: flat_links is None or empty.")

        if self.exp_links is not None:
            return self.exp_links

        exp_links = [self.flat_links[0]]
        genome.Genome.expandLinks(self.flat_links[0], 
                                self.flat_links[0].name, 
                                self.flat_links, 
                                exp_links)
        self.exp_links = exp_links
        return self.exp_links
    def get_joints(self):
        self.get_expanded_links()
        return self.exp_links  # or filter as needed

    def get_muscles(self):
        self.get_expanded_links()
        muscles = []
        for link in self.exp_links:
            if hasattr(link, 'parent') and link.parent is not None:
                class Muscle:
                    def __init__(self, joint_a, joint_b):
                        self.joint_a = joint_a
                        self.joint_b = joint_b
                muscles.append(Muscle(link, link.parent))
        return muscles
    def to_xml(self):
        self.get_expanded_links()
        domimpl = getDOMImplementation()
        adom = domimpl.createDocument(None, "start", None)
        robot_tag = adom.createElement("robot")
        for link in self.exp_links:
            robot_tag.appendChild(link.to_link_element(adom))
        first = True
        for link in self.exp_links:
            if first:# skip the root node! 
                first = False
                continue
            robot_tag.appendChild(link.to_joint_element(adom))
        robot_tag.setAttribute("name", "pepe") #  choose a name!
        return '<?xml version="1.0"?>' + robot_tag.toprettyxml()

    def get_motors(self):
        self.get_expanded_links()
        if self.motors == None:
            motors = []
            for i in range(1, len(self.exp_links)):
                l = self.exp_links[i]
                m = Motor(l.control_waveform, l.control_amp,  l.control_freq)
                motors.append(m)
            self.motors = motors 
        return self.motors 
    
    def update_position(self, pos):
        if self.start_position == None:
            self.start_position = pos
        else:
            self.last_position = pos

    def get_distance_travelled(self):
        if self.start_position is None or self.last_position is None:
            return 0
        p1 = np.asarray(self.start_position)
        p2 = np.asarray(self.last_position)
        dist = np.linalg.norm(p1-p2)
        return dist 
    def set_peak_pos(self, pos):
        self.peak_pos = pos
        
    
    def get_distance_to_peak(self):
        if self.last_position is None or self.peak_pos is None:
            return 0
        return np.linalg.norm(np.asarray(self.last_position) - np.asarray(self.peak_pos))
    
    def check_tiny_parts(self):
        penalty = 0
        tiny_joint_count = 0
        tiny_muscle_count = 0

        joints = self.get_joints()
        muscles = self.get_muscles()

        for joint in joints:
            if hasattr(joint, 'radius') and joint.radius < self.MIN_JOINT_RADIUS:
                tiny_joint_count += 1

        for muscle in muscles:
            joint_a = muscle.joint_a
            joint_b = muscle.joint_b
            
            length = None
            if hasattr(joint_a, 'link_length') and hasattr(joint_b, 'link_length'):
                length = abs(joint_a.link_length - joint_b.link_length)
            
            if length is None:
                length = 0.0

            if length < self.MIN_MUSCLE_LENGTH:
                tiny_muscle_count += 1

        total_tiny_parts = tiny_joint_count + tiny_muscle_count
        penalty = self.TINY_PART_PENALTY * total_tiny_parts

        return penalty, tiny_joint_count, tiny_muscle_count
    
    def check_large_parts(self):
        penalty = 0
        large_joint_count = 0
        large_muscle_count = 0

        joints = self.get_joints()
        muscles = self.get_muscles()

        for joint in joints:
            if hasattr(joint, 'radius') and joint.radius > self.MAX_JOINT_RADIUS:
                large_joint_count += 1

        for muscle in muscles:
            joint_a = muscle.joint_a
            joint_b = muscle.joint_b
            length = None
            if hasattr(joint_a, 'link_length') and hasattr(joint_b, 'link_length'):
                length = abs(joint_a.link_length - joint_b.link_length)

            if length is None:
                length = 0.0

            if length > self.MAX_MUSCLE_LENGTH:
                large_muscle_count += 1

        total_large_parts = large_joint_count + large_muscle_count
        penalty = self.LARGE_PART_PENALTY * total_large_parts

        return penalty, large_joint_count, large_muscle_count
    
    def check_too_simple(self):
        joints = len(self.get_joints())
        muscles = len(self.get_muscles())
        
        penalty = 0
        if joints < self.MIN_JOINT_COUNT:
            penalty += self.SIMPLE_CREATURE_PENALTY
        if muscles < self.MIN_MUSCLE_COUNT:
            penalty += self.SIMPLE_CREATURE_PENALTY
        
        return penalty, joints, muscles

    def update_dna(self, dna):
        self.dna = dna
        self.flat_links = None
        self.exp_links = None
        self.motors = None
        self.start_position = None
        self.last_position = None