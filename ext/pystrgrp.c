#include <Python.h>
#include "strgrp.h"

//
// strgrp_item
//

typedef struct {
    PyObject_HEAD;
    struct strgrp_item *item;
} ItemObject;

static void
Item_dealloc(PyObject *obj) {
    Py_TYPE(obj)->tp_free(obj);
}

static PyObject *
Item_key(ItemObject *self) {
    char *key = strgrp_item_key(self->item);
    PyObject *py_key = Py_BuildValue("s", key);
    Py_XINCREF(py_key);
    return py_key;
}

static PyObject *
Item_value(ItemObject *self) {
    PyObject *value = strgrp_item_value(self->item);
    Py_XINCREF(value);
    return value;
}

static PyMethodDef Item_methods[] = {
    { "key", (PyCFunction)Item_key, METH_NOARGS,
        "Fetch the description stored in the item" },
    { "value", (PyCFunction)Item_value, METH_NOARGS,
        "Fetch the data stored in the item" },
    {NULL}
};

static PyTypeObject ItemType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "strgrp.Item",           /* tp_name */
    sizeof(ItemObject),      /* tp_basicsize */
    0,                         /* tp_itemsize */
    &Item_dealloc,            /* tp_dealloc */
    0,                         /* tp_print */
    0,                         /* tp_getattr */
    0,                         /* tp_setattr */
    0,                         /* tp_reserved */
    0,                         /* tp_repr */
    0,                         /* tp_as_number */
    0,                         /* tp_as_sequence */
    0,                         /* tp_as_mapping */
    0,                         /* tp_hash  */
    0,                         /* tp_call */
    0,                         /* tp_str */
    0,                         /* tp_getattro */
    0,                         /* tp_setattro */
    0,                         /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT,        /* tp_flags */
    "Item object",           /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    Item_methods,                         /* tp_methods */
    0,                         /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    0,                         /* tp_init */
    0,                         /* tp_alloc */
};

//
// strgrp_bin
//

typedef struct {
    PyObject_HEAD;
    struct strgrp_bin *bin;
    struct strgrp_bin_iter *iter;
} BinObject;

static void
Bin_dealloc(PyObject *obj) {
    BinObject *self = (BinObject *)obj;
    if (self->iter) {
        strgrp_bin_iter_free(self->iter);
    }
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static PyObject *
Bin_iter(PyObject *self) {
    Py_INCREF(self);
    return self;
}

static PyObject *
Bin_iternext(BinObject *self) {
    if (!self->iter) {
        self->iter = strgrp_bin_iter_new(self->bin);
        if (!self->iter) {
            return PyErr_NoMemory();
        }
    }
    ItemObject *item = (ItemObject *)PyType_GenericNew(&ItemType, NULL, NULL);
    if (!item) {
        return PyErr_NoMemory();
    }
    item->item = strgrp_bin_iter_next(self->iter);
    if (!item->item) {
        Item_dealloc((PyObject *)item);
        self->iter = NULL;
        /* Raising of standard StopIteration exception with empty value. */
        PyErr_SetNone(PyExc_StopIteration);
        return NULL;
    }
    return (PyObject *)item;
}

static PyObject *
Bin_key(BinObject *self) {
    char *key = strgrp_bin_key(self->bin);
    PyObject *py_key = Py_BuildValue("s", key);
    Py_XINCREF(py_key);
    return py_key;
}

static PyMethodDef Bin_methods[] = {
    { "key", (PyCFunction)Bin_key, METH_NOARGS,
        "Fetch the description stored in the item" },
    {NULL}
};

static PyTypeObject BinType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "strgrp.Bin",           /* tp_name */
    sizeof(BinObject),      /* tp_basicsize */
    0,                         /* tp_itemsize */
    &Bin_dealloc,            /* tp_dealloc */
    0,                         /* tp_print */
    0,                         /* tp_getattr */
    0,                         /* tp_setattr */
    0,                         /* tp_reserved */
    0,                         /* tp_repr */
    0,                         /* tp_as_number */
    0,                         /* tp_as_sequence */
    0,                         /* tp_as_mapping */
    0,                         /* tp_hash  */
    0,                         /* tp_call */
    0,                         /* tp_str */
    0,                         /* tp_getattro */
    0,                         /* tp_setattro */
    0,                         /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT,        /* tp_flags */
    "Bin object",           /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    (getiterfunc) &Bin_iter,                         /* tp_iter */
    (iternextfunc) &Bin_iternext,                         /* tp_iternext */
    Bin_methods,                         /* tp_methods */
    0,                         /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    0,                         /* tp_init */
    0,                         /* tp_alloc */
};

//
// Strgrp
//

typedef struct {
    PyObject_HEAD;
    double thresh;
    struct strgrp *grp;
    struct strgrp_iter *iter;
} StrgrpObject;

static PyObject *
Strgrp_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    StrgrpObject *self = (StrgrpObject *)type->tp_alloc(type, 0);
    if (self != NULL) {
        self->thresh = 0.85;
        self->grp = NULL;
    }
    return (PyObject *)self;
}

static int
Strgrp_init(StrgrpObject *self, PyObject *args, PyObject *kwds) {
    double threshold = self->thresh;
    static char *kwlist[] = {"threshold", NULL};
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|d", kwlist, &threshold)) {
        return -1;
    }
    self->grp = strgrp_new(threshold);
    if (!self->grp) {
        return -1;
    }
    return 0;
}

static void
xdecref(void *data) {
    Py_XDECREF((PyObject *)data);
}

static void
Strgrp_dealloc(PyObject *obj) {
    StrgrpObject *self = (StrgrpObject *)obj;
    strgrp_free_cb(self->grp, &xdecref);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static PyObject *
Strgrp_add(StrgrpObject *self, PyObject *args, PyObject *kwds) {
    char *key;
    PyObject *data = NULL;
    static char *kwlist[] = { "key", "data", NULL };
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "sO", kwlist, &key, &data)) {
        return NULL;
    }
    if (!data) {
        return NULL;
    }
    Py_INCREF(data);
    struct strgrp_bin * bin = strgrp_add(self->grp, key, data);
    if (!bin) {
        return PyErr_NoMemory();
    }
    BinObject * const binobj = (BinObject *)PyType_GenericNew(&BinType, NULL, NULL);
    if (!binobj) {
        return PyErr_NoMemory();
    }
    binobj->bin = bin;
    return (PyObject *)binobj;
}

static PyObject *
Strgrp_iter(PyObject *self) {
    Py_INCREF(self);
    return self;
}

static PyObject *
Strgrp_iternext(StrgrpObject *self) {
    if (!self->iter) {
        self->iter = strgrp_iter_new(self->grp);
        if (!self->iter) {
            return PyErr_NoMemory();
        }
    }
    BinObject *bin = (BinObject *)PyType_GenericNew(&BinType, NULL, NULL);
    if (!bin) {
        return PyErr_NoMemory();
    }
    bin->bin = strgrp_iter_next(self->iter);
    if (!bin->bin) {
        Bin_dealloc((PyObject *)bin);
        self->iter = NULL;
        /* Raising of standard StopIteration exception with empty value. */
        PyErr_SetNone(PyExc_StopIteration);
        return NULL;
    }
    return (PyObject *)bin;
}

static PyMethodDef Strgrp_methods[] = {
    { "add", (PyCFunction)Strgrp_add, (METH_VARARGS | METH_KEYWORDS),
        "Classify a string into a bin" },
    {NULL}
};

static PyTypeObject StrgrpType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "strgrp.Strgrp",           /* tp_name */
    sizeof(StrgrpObject),      /* tp_basicsize */
    0,                         /* tp_itemsize */
    &Strgrp_dealloc,            /* tp_dealloc */
    0,                         /* tp_print */
    0,                         /* tp_getattr */
    0,                         /* tp_setattr */
    0,                         /* tp_reserved */
    0,                         /* tp_repr */
    0,                         /* tp_as_number */
    0,                         /* tp_as_sequence */
    0,                         /* tp_as_mapping */
    0,                         /* tp_hash  */
    0,                         /* tp_call */
    0,                         /* tp_str */
    0,                         /* tp_getattro */
    0,                         /* tp_setattro */
    0,                         /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT,        /* tp_flags */
    "Strgrp object",           /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    (getiterfunc) &Strgrp_iter,                         /* tp_iter */
    (iternextfunc) &Strgrp_iternext,                         /* tp_iternext */
    Strgrp_methods,            /* tp_methods */
    0,                         /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc) &Strgrp_init,     /* tp_init */
    0,                         /* tp_alloc */
    Strgrp_new,                /* tp_new */
};

static PyModuleDef StrgrpModule = {
    PyModuleDef_HEAD_INIT,
    "strgrp",
    "Group similar strings into bins",
    -1,
    NULL, NULL, NULL, NULL, NULL
};

PyMODINIT_FUNC
PyInit_pystrgrp(void) 
{
    PyObject* m;

    ItemType.tp_new = &PyType_GenericNew;
    if (PyType_Ready(&ItemType) < 0) {
        return NULL;
    }

    BinType.tp_new = &PyType_GenericNew;
    if (PyType_Ready(&BinType) < 0) {
        return NULL;
    }

    if (PyType_Ready(&StrgrpType) < 0) {
        return NULL;
    }

    m = PyModule_Create(&StrgrpModule);
    if (m == NULL)
        return NULL;

    Py_INCREF(&StrgrpType);
    PyModule_AddObject(m, "Strgrp", (PyObject *)&StrgrpType);
    return m;
}
