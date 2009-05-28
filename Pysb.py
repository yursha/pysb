import sys


class SelfExporter(object):
    """Expects a constructor paramter 'name', under which this object is
    inserted into the __main__ namespace."""

    do_self_export = True
    default_model = None

    def __init__(self, name):
        self.name = name

        if SelfExporter.do_self_export:
            if isinstance(self, Model):
                if SelfExporter.default_model != None:
                    raise Exception("Only one instance of Model may be declared ('%s' previously declared)" % SelfExporter.default_model.name)
                SelfExporter.default_model = self
            elif isinstance(self, (Monomer, Compartment, Parameter, Rule)):
                if SelfExporter.default_model == None:
                    raise Exception("A Model must be declared before declaring any model components")
                SelfExporter.default_model.add_component(self)

            # load self into __main__ namespace
            main = sys.modules['__main__']
            if hasattr(main, name):
                raise Exception("'%s' already defined" % (name))
            setattr(main, name, self)



class Model(SelfExporter):
    def __init__(self, name):
        SelfExporter.__init__(self, name)
        self.monomers = []
        self.compartments = []
        self.parameters = []
        self.rules = []

    def add_component(self, other):
        if isinstance(other, Monomer):
            self.monomers.append(other)
        elif isinstance(other, Compartment):
            self.compartments.append(other)
        elif isinstance(other, Parameter):
            self.parameters.append(other)
        elif isinstance(other, Rule):
            self.rules.append(other)
        else:
            raise Exception("Tried to add component of unknown type (%s) to model" % type(other))

    



class Monomer(SelfExporter):
    def __init__(self, name, sites=[], site_states={}, compartment=None):
        SelfExporter.__init__(self, name)
        
        # ensure no duplicate sites
        sites_seen = {}
        for site in sites:
            sites_seen.setdefault(site, 0)
            sites_seen[site] += 1
        sites_dup = [site for site in sites_seen.keys() if sites_seen[site] > 1]
        if sites_dup:
            raise Exception("Duplicate sites specified: " + str(sites_dup))

        # ensure site_states keys are all known sites
        unknown_sites = [site for site in site_states.keys() if not site in self.sites_dict]
        if unknown_sites:
            raise Exception("Unknown sites in site_states: " + str(unknown_sites))
        # ensure site_states values are all strings
        invalid_sites = [site for (site, states) in site_states.items() if not all([type(s) == str for s in states])]
        if invalid_sites:
            raise Exception("Non-string state values in site_states for sites: " + str(invalid_sites))

        # ensure compartment is a Compartment
        if compartment and not isinstance(compartment, Compartment):
            raise Exception("compartment is not a Compartment object")

        self.sites = sites
        self.sites_dict = dict.fromkeys(sites)
        self.site_states = site_states
        self.compartment = compartment

    def __call__(self, **site_conditions):
        """Build a pattern object with convenient kwargs for the sites"""
        compartment = site_conditions.pop('compartment', self.compartment)
        return MonomerPattern(self, site_conditions, compartment)

    def __str__(self):
        return self.name + '(' + ', '.join(self.sites) + ')'




class MonomerPattern:
    def __init__(self, monomer, site_conditions, compartment):
        # ensure all keys in site_conditions are sites in monomer
        unknown_sites = [site for site in site_conditions.keys() if site not in monomer.sites_dict]
        if unknown_sites:
            raise Exception("Unknown sites in " + str(monomer) + ": " + str(unknown_sites))

        # ensure each value is None, integer, Monomer, or list of Monomers
        invalid_sites = []
        for (site, state) in site_conditions.items():
            # convert singleton monomer to list
            if isinstance(state, Monomer):
                state = [state]
                site_conditions[site] = state
            # pass through to next iteration if state type is ok
            if state == None:
                continue
            elif type(state) == int:
                continue
            elif type(state) == list and all([isinstance(s, Monomer) for s in state]):
                continue
            invalid_sites.append(site)
        if invalid_sites:
            raise Exception("Invalid state value for sites: " + str(invalid_sites))

        # ensure compartment is a Compartment
        if compartment and not isinstance(compartment, Compartment):
            raise Exception("compartment is not a Compartment object")

        self.monomer = monomer
        self.site_conditions = site_conditions
        self.compartment = compartment

    def __add__(self, other):
        if isinstance(other, MonomerPattern):
            return [self, other]
        else: 
            return NotImplemented

    def __radd__(self, other):
        if isinstance(other, list) and all(isinstance(v, MonomerPattern) for v in other):
            return [self] + other
        else:
            return NotImplemented
        

    def __str__(self):
        return self.monomer.name + '(' + ', '.join([k + '=' + str(self.site_conditions[k])
                                                    for k in self.site_conditions.keys()]) + ')'



class ReactionPattern:
    def __init__(self, monomer_patterns):
        monomer_patterns = this.monomer_patterns

    def __rshift__(self, other):
        return Rule(name, self.monomer_patterns, other.monomer_patterns)



class Parameter(SelfExporter):
    def __init__(self, name, value=float('nan')):
        SelfExporter.__init__(self, name)
        self.value = value




class Compartment(SelfExporter):
    # FIXME: sane defaults?
    def __init__(self, name, neighbors=[], dimension=3, size=1):
        SelfExporter.__init__(self, name)

        if not all([isinstance(n, Compartment) for n in neighbors]):
            raise Exception("neighbors must all be Compartments")

        self.neighbors = neighbors
        self.dimension = dimension
        self.size = size




class Rule(SelfExporter):
    def __init__(self, name, reactants, products, rate):
        SelfExporter.__init__(self, name)

        if not all([isinstance(r, MonomerPattern) for r in reactants]):
            raise Exception("Reactants must all be MonomerPatterns")
        if not all([isinstance(p, MonomerPattern) for p in products]):
            raise Exception("Products must all be MonomerPatterns")
        if not isinstance(rate, Parameter):
            raise Exception("Rate must be a Parameter")

        self.reactants = reactants
        self.products = products
        self.rate = rate
        # TODO: ensure all numbered sites are referenced exactly twice within each of reactants and products
