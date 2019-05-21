import tempfile
import zipfile
import yaml
import os
from chimerax.core import models, io
from chimerax.core.commands import run, concise_model_spec


class GaudiModel(object):
    def __init__(self, path, session, *args, **kwargs):
        self.path = path
        self.basedir = os.path.dirname(path)
        self.data, self.headers, self.keys = self.parse()
        self.tempdir = tempfile.mkdtemp("gaudiviewx")
        self.session = session

    def parse(self):
        with open(self.path, "r") as f:
            data = yaml.load(f)
        datarray = [[k] + v for k, v in data["GAUDI.results"].items()]
        keys = data["GAUDI.results"].keys()
        header = ["Filename"] + list(
            map(lambda text: text.split()[0], data["GAUDI.results"])
        )
        return datarray, header, keys

    def parse_zip(self, path):
        name = os.path.splitext(os.path.basename(path))[0]
        try:
            z = zipfile.ZipFile(path)
        except:
            print("{} is not a valid GAUDI result".format(path))
        else:
            tmp = os.path.join(self.tempdir, name)
            try:
                os.mkdir(tmp)
            except OSError:
                pass
            z.extractall(tmp)
            mol2 = [
                os.path.join(tmp, name)
                for name in z.namelist()
                if name.endswith(".mol2")
            ]

            if len(mol2) > 1:
                models, status = io.open_multiple_data(
                    self.session, mol2, format=None, name=name
                )
            else:
                models, status = io.open_data(
                    self.session, mol2[0], format=None, name=name
                )
            z.close()
            return models

    def save_models(self):
        modelsdict = {}

        for key in self.keys:
            models = self.parse_zip(os.path.join(self.basedir, key))
            modelsdict[key] = models
        return modelsdict
