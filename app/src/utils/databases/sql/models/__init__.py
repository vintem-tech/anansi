from pony.orm import commit

class UpdateAttributesDict(object):
    def update_attributes_dict(self, **kwargs):
        for attribute, value in kwargs.items():
            setattr(self, attribute, value)
            commit()
