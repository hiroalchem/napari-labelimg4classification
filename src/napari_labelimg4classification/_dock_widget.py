from pathlib import Path
import os

from skimage import io
import pandas as pd

from qtpy.QtWidgets import QWidget, QVBoxLayout, QLineEdit
from magicgui.widgets import FileEdit, Select, Label, CheckBox
from napari_plugin_engine import napari_hook_implementation
from napari_tools_menu import register_dock_widget


@register_dock_widget(menu="Utilities > label tool for classification")
class L4CWidget(QWidget):
    def __init__(self, napari_viewer):
        super().__init__()
        self._viewer = napari_viewer
        self.setLayout(QVBoxLayout())
        self.target_dir = FileEdit(mode='d')
        self.layout().addWidget(self.target_dir.native)
        self.target_dir.changed.connect(self.load_dir)
        self.checkbox = CheckBox(text='split channels')
        self.layout().addWidget(self.checkbox.native)
        self.Label1 = Label(value='file list')
        self.layout().addWidget(self.Label1.native)
        self.image_lists = []
        self.df = pd.DataFrame()
        self.images = Select(choices=self.image_lists, allow_multiple=False)
        self.images.changed.connect(self.load_image)
        self.layout().addWidget(self.images.native)
        self.Label2 = Label(value='class list')
        self.layout().addWidget(self.Label2.native)
        self.classlist = []
        self.selection = Select(allow_multiple=True)
        self.selection.changed.connect(self.save_choice)
        self.layout().addWidget(self.selection.native)
        self.Label3 = Label(value='add/delete class')
        self.layout().addWidget(self.Label3.native)
        self.lineEdit = QLineEdit()
        self.layout().addWidget(self.lineEdit)
        self.lineEdit.returnPressed.connect(self.addList)
        self.image_layer = None

    def load_dir(self):
        imgs = sorted(list(Path(self.target_dir.value).glob('./**/*png')) + list(Path(self.target_dir.value).glob('./**/*tif')))
        imgs = [str(x.relative_to(Path(self.target_dir.value))) for x in imgs]
        self.image_lists = imgs
        self.images.choices = self.image_lists
        self.df = pd.DataFrame({'label': [''] * len(self.image_lists)}, index=self.image_lists).astype(str)
        # load previous csv and merge
        try:
            prev_df = pd.read_csv(os.path.join(self.target_dir.value, 'labels.csv'), index_col=0).fillna('').astype(str)
            self.df.update(prev_df)
        except:
            pass

        # load class fle
        try:
            with open(os.path.join(self.target_dir.value, 'class.txt'), mode='r') as f:
                lines = f.read().splitlines()
                for line in lines:
                    if line not in self.classlist:
                        self.classlist.append(line)
                    else:
                       pass
            class_from_df = list(set(self.df['label']))
            for c in class_from_df:
                if (c not in self.classlist) and c != '':
                    self.classlist.append(c)
                else:
                    pass
            self.selection.choices = self.classlist
        except:
            pass

    def load_image(self):
        img = io.imread(os.path.join(self.target_dir.value, self.images.value[0]))
        layer_names = []
        colors_dict = {}
        cl_dict = {}
        d_dict = {}
        for i, layer in enumerate(self._viewer.layers):
            if 'l4c_images' in layer.name:
                if 'ch' in layer.name:
                    colors_dict[layer.name.split('ch')[1]] = layer.colormap.name
                    cl_dict[layer.name.split('ch')[1]] = layer.contrast_limits
                    d_dict[layer.name.split('ch')[1]] = layer.data.dtype
                else:
                    pass
                layer_names.append(layer.name)
            else:
                pass
        for name in layer_names:
            del self._viewer.layers[name]
        if self.checkbox.value:
            _, _, channels = img.shape
            for c in range(channels):
                if str(c) in colors_dict:
                    color = colors_dict[str(c)]
                    if d_dict[str(c)] == img.dtype:
                        cl_new = cl_dict[str(c)]
                        print(cl_new)
                    else:
                        cl_new = None
                else:
                    color = 'gray'
                    cl_new = None
                if img.dtype == 'uint8':
                    cl = [0, 255]
                elif img.dtype == 'uint16':
                    cl = [0, 65535]
                else:
                    cl = None
                self.image_layer = self._viewer.add_image(img[:, :, c], name=f'l4c_images_ch{c}', blending='additive'
                                                          , colormap=color, contrast_limits=cl)
                if cl_new:
                    self.image_layer.contrast_limits = cl_new
                else:
                    pass
        else:
            self.image_layer = self._viewer.add_image(img, name='l4c_images')

        # load label
        print(self.images.value[0], self.df.at[self.images.value[0], 'label'])
        if self.df.at[self.images.value[0], 'label'] in self.selection.choices:
            with self.selection.changed.blocked():
                self.selection.value = self.df.at[self.images.value[0], 'label']
                print('value set to', self.df.at[self.images.value[0], 'label'], self.selection.value)
        else:
            with self.selection.changed.blocked():
                self.selection.value = []
                print('reset', self.selection.value)

    def save_choice(self):
        if len(self.selection.value) != 1:
            pass
        else:
            self.df.at[self.images.value[0], 'label'] = self.selection.value[0]
            self.df.to_csv(os.path.join(self.target_dir.value, 'labels.csv'))

    def addList(self):
        text = self.lineEdit.text()
        if text in self.classlist:
            self.classlist.remove(text)
        else:
            self.classlist.append(text)
        self.selection.choices = self.classlist
        self.lineEdit.clear()
        # save class file
        with open(os.path.join(self.target_dir.value, 'class.txt'), mode='w') as f:
            f.write('\n'.join(list(self.selection.choices)))


@napari_hook_implementation
def napari_experimental_provide_dock_widget():
    return [L4CWidget]
