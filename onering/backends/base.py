import os
import json
from onering import utils



class TargetBackend(object):
    """
    Interface for all target (languages/platforms) that can generate transformers.
    """
    def generate_transformer(self, onering, instance_transformer, output_path, **kwargs):
        pass

