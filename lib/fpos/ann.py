import hashlib
import os
import pygenann
import xdg

def to_input(string):
    return [float(ord(x)) for x in string]

salt = "382a55c995b1e53f3ad0a3ed1c5ae735b9c7adc0".encode("UTF-8")

class DescriptionAnn(object):
    def __init__(self, cache=None, ann=None, inputs=100, layers=1, hidden=100, outputs=1, description=None):
        if cache is None:
            cache = DescriptionAnn.get_data_dir()
        self.data_dir = cache

        if ann is None:
            ann = pygenann.genann(inputs, layers, hidden, outputs)
        self.ann = ann

        if description is None:
            self.canonical_path = None
        else:
            self.canonical_path = DescriptionAnn.derive_canonical(self.data_dir, description)


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
            ann = pygenann.genann.read(path)
            return DescriptionAnn(cache=cache, ann=ann)
        return DescriptionAnn(cache=cache, inputs=100, layers=1, hidden=100, outputs=1)

    @staticmethod
    def get_canonical(path):
        if os.path.islink(path):
            return os.path.readlink(path)
        return path

    @staticmethod
    def derive_canonical(data_dir, description):
        did = DescriptionAnn.gen_id(description, salt)
        dentries = DescriptionAnn.gen_rel_dentries(did)
        path = os.path.join(data_dir, *dentries)
        DescriptionAnn.ensure_dir(data_dir, dentries)
        return DescriptionAnn.get_canonical(path)

    def cache(self, description):
        did = DescriptionAnn.gen_id(description, salt)
        dentries = DescriptionAnn.gen_rel_dentries(did)
        path = os.path.join(self.data_dir, *dentries)
        DescriptionAnn.ensure_dir(self.data_dir, dentries)
        if self.canonical_path is None:
            self.canonical_path = DescriptionAnn.get_canonical(path)

        if (not os.path.exists(self.canonical_path)
                or self.canonical_path == path):
            self.ann.write(path)
            return

        if not os.path.exists(path):
            os.symlink(self.canonical_path, path)

        self.ann.write(self.canonical_path)

    def write(self):
        assert(self.canonical_path is not None)
        self.ann.write(self.canonical_path)

    def accept(self, description, iters=300, write=True):
        ret = self.ann.train(to_input(description), [1.0], 3, iters=iters)
        if write:
            self.cache(description)
        return ret

    def reject(self, description, iters=300, write=False):
        ret = self.ann.train(to_input(description), [0.0], 3, iters=iters)
        if write:
            self.write()
        return

    def run(self, description):
        return self.ann.run(to_input(description))[0]
