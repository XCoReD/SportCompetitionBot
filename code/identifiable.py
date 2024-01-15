"""I still cannot think in Pythonic way. I need interfaces."""
class Identifiable:
    '''The base abstract class for handling different logic flows, definitely, non-Pythonic way'''
    @property
    def id(self):
        raise NotImplementedError
