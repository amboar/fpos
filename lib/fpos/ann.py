import hashlib
import os
import pygenann
import xdg

def to_input(string):
    return [float(ord(x)) for x in string]

salt = "382a55c995b1e53f3ad0a3ed1c5ae735b9c7adc0".encode("UTF-8")

class DescriptionAnn(object):
    def __init__(self, cache=None, ann=None, inputs=100, layers=1, hidden=100, outputs=1):
        if cache is None:
            cache = DescriptionAnn.get_data_dir()
        self.data_dir = cache

        if ann is None:
            ann = pygenann.genann(inputs, layers, hidden, outputs)
        self.ann = ann

    @staticmethod
    def get_data_dir(head=None, tail=None):
        if head is None:
            head = str(xdg.BaseDirectory.save_data_path("fpos"))
        if tail is None:
            tail = ("ann", "descriptions")
        return os.path.join(head, *tail)

    @staticmethod
    def gen_id(description, salt):
        s = hashlib.sha1()
        s.update(str(description).encode("UTF-8"))
        s.update(salt)
        return s.hexdigest()

    @staticmethod
    def gen_rel_dentries(did):
        return did[:2], did[2:]

    @staticmethod
    def ensure_dir(data_dir, dentries):
        assert(os.path.exists(data_dir))
        abspath = os.path.join(data_dir, dentries[0])
        if not os.path.exists(abspath):
            os.mkdir(abspath)

    @staticmethod
    def have_ann(path):
        return os.path.exists(path)

    @staticmethod
    def load(description, cache=None):
        if cache is None:
            cache = DescriptionAnn.get_data_dir()
        did = DescriptionAnn.gen_id(description, salt)
        dentries = DescriptionAnn.gen_rel_dentries(did)
        path = os.path.join(cache, *dentries)
        if DescriptionAnn.have_ann(path):
            print("Loading ANN at {}".format(path))
            ann = pygenann.genann.read(path)
            return DescriptionAnn(cache=cache, ann=ann)
        print("No ANN found at {}, instantiating new".format(path))
        return DescriptionAnn(cache=cache, inputs=100, layers=1, hidden=100, outputs=1)

    @staticmethod
    def get_canonical(path):
        if os.path.islink(path):
            return os.path.readlink(path)
        return path

    def cache_ann(self, description, **kwargs):
        did = DescriptionAnn.gen_id(description, salt)
        dentries = DescriptionAnn.gen_rel_dentries(did)
        path = os.path.join(self.data_dir, *dentries)
        DescriptionAnn.ensure_dir(self.data_dir, dentries)
        c = DescriptionAnn.get_canonical(path)

        if not os.path.exists(c) or c == path:
            self.ann.write(path)
            return

        if not os.path.exists(path):
            os.symlink(c, path)

        self.ann.write(path)

    def accept(self, description):
        try:
            return self.ann.train(to_input(description), [1.0], 3)
        finally:
            self.cache_ann(description)


    def reject(self, description):
        return self.ann.train(to_input(description), [0.0], 3)

    def run(self, description):
        return self.ann.run(to_input(description))[0]
