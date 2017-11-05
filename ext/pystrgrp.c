#include <Python.h>
#include "ccan/strgrp/strgrp.h"

//
// strgrp_item
//

typedef struct {
    PyObject_HEAD;
    const struct strgrp_item *item;
} ItemObject;

static void
Item_dealloc(PyObject *obj) {
    Py_TYPE(obj)->tp_free(obj);
}

static PyObject *
Item_key(ItemObject *self) {
    const char *key = strgrp_item_key(self->item);
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
// strgrp_grp
//

typedef struct {
    PyObject_HEAD;
    struct strgrp_grp *grp;
    struct strgrp_grp_iter *iter;
} GrpObject;

static void
Grp_dealloc(PyObject *obj) {
    GrpObject *self = (GrpObject *)obj;
    if (self->iter) {
        strgrp_grp_iter_free(self->iter);
    }
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static PyObject *
Grp_iter(PyObject *self) {
    Py_INCREF(self);
    return self;
}

static PyObject *
Grp_iternext(GrpObject *self) {
    if (!self->iter) {
        self->iter = strgrp_grp_iter_new(self->grp);
        if (!self->iter) {
            return PyErr_NoMemory();
        }
    }
    ItemObject *item = (ItemObject *)PyType_GenericNew(&ItemType, NULL, NULL);
    if (!item) {
        return PyErr_NoMemory();
    }
    item->item = strgrp_grp_iter_next(self->iter);
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
Grp_key(GrpObject *self) {
    const char *key = strgrp_grp_key(self->grp);
    PyObject *py_key = Py_BuildValue("s", key);
    Py_XINCREF(py_key);
    return py_key;
}

static PyObject *
Grp_add(GrpObject *self, PyObject *args, PyObject *kwds) {
    char *key;
    PyObject *data = NULL;
    static char *kwlist[] = { "key", "data", NULL };
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "sO", kwlist, &key, &data)) {
        return NULL;
    }

    if (!data) {
        return NULL;
    }

    const bool added = strgrp_grp_add(self->grp, key, data);
    if (added) {
        Py_INCREF(data);
        Py_RETURN_TRUE;
    }

    Py_RETURN_FALSE;
}

static PyMethodDef Grp_methods[] = {
    { "key", (PyCFunction)Grp_key, METH_NOARGS,
        "Fetch the description stored in the item" },
    { "add", (PyCFunction)Grp_add, (METH_VARARGS | METH_KEYWORDS),
        "Add a string and its associated data to a group" },
    {NULL}
};

static PyTypeObject GrpType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "strgrp.Grp",           /* tp_name */
    sizeof(GrpObject),      /* tp_basicsize */
    0,                         /* tp_itemsize */
    &Grp_dealloc,            /* tp_dealloc */
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
    "Grp object",           /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    (getiterfunc) &Grp_iter,                         /* tp_iter */
    (iternextfunc) &Grp_iternext,                         /* tp_iternext */
    Grp_methods,                         /* tp_methods */
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
Strgrp_grp_for(StrgrpObject *self, PyObject *args, PyObject *kwds) {
    char *key;
    static char *kwlist[] = { "key", NULL };
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "s", kwlist, &key)) {
        return NULL;
    }
    struct strgrp_grp * grp = strgrp_grp_for(self->grp, key);
    if (!grp) {
        Py_RETURN_NONE;
    }
    GrpObject * const grpobj = (GrpObject *)PyType_GenericNew(&GrpType, NULL, NULL);
    if (!grpobj) {
        return PyErr_NoMemory();
    }
    grpobj->grp = grp;
    return (PyObject *)grpobj;
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
    struct strgrp_grp * grp = strgrp_add(self->grp, key, data);
    if (!grp) {
        return PyErr_NoMemory();
    }
    GrpObject * const grpobj = (GrpObject *)PyType_GenericNew(&GrpType, NULL, NULL);
    if (!grpobj) {
        return PyErr_NoMemory();
    }
    grpobj->grp = grp;
    return (PyObject *)grpobj;
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
    GrpObject *grp = (GrpObject *)PyType_GenericNew(&GrpType, NULL, NULL);
    if (!grp) {
        return PyErr_NoMemory();
    }
    grp->grp = strgrp_iter_next(self->iter);
    if (!grp->grp) {
        Grp_dealloc((PyObject *)grp);
        self->iter = NULL;
        /* Raising of standard StopIteration exception with empty value. */
        PyErr_SetNone(PyExc_StopIteration);
        return NULL;
    }
    return (PyObject *)grp;
}

static PyObject *
Strgrp_grp_exact(StrgrpObject *self, PyObject *args, PyObject *kwds) {
    char *key;
    static char *kwlist[] = { "key", NULL };
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "s", kwlist, &key)) {
        return NULL;
    }
    struct strgrp_grp * grp = strgrp_grp_exact(self->grp, key);
    if (!grp) {
        Py_RETURN_NONE;
    }
    GrpObject * const grpobj = (GrpObject *)PyType_GenericNew(&GrpType, NULL, NULL);
    if (!grpobj) {
        return PyErr_NoMemory();
    }
    grpobj->grp = grp;
    return (PyObject *)grpobj;
}

static PyObject *
Strgrp_grps_for(StrgrpObject *self, PyObject *args, PyObject *kwds) {
    char *key;
    static char *kwlist[] = { "key", NULL };
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "s", kwlist, &key)) {
        return NULL;
    }

    struct heap *heap = strgrp_grps_for(self->grp, key);
    if (!heap) {
        Py_RETURN_NONE;
    }

    PyObject *tupleobj = PyTuple_New(heap->len);
    if (!tupleobj) {
        PyErr_NoMemory();
        goto cleanup_heap;
    }

    struct strgrp_grp *grp;
    Py_ssize_t i;
    for (i = 0; (grp = heap_pop(heap)); i++) {
        GrpObject *const grpobj = (GrpObject *)PyType_GenericNew(&GrpType, NULL, NULL);
        if (!grpobj) {
            goto cleanup_tuple;
        }
        grpobj->grp = grp;
        if (PyTuple_SetItem(tupleobj, i, (PyObject *)grpobj)) {
            Py_XDECREF((PyObject *)grpobj);
            goto cleanup_tuple;
        };
    }

    heap_free(heap);

    return (PyObject *)tupleobj;

cleanup_tuple:
    while (--i >= 0) {
        Py_XDECREF((PyObject *)PyTuple_GetItem(tupleobj, i));
    }
    Py_XDECREF((PyObject *)tupleobj);

cleanup_heap:
    heap_free(heap);

    return NULL;
}

static PyMethodDef Strgrp_methods[] = {
    { "add", (PyCFunction)Strgrp_add, (METH_VARARGS | METH_KEYWORDS),
        "Cluster a string" },
    { "grp_for", (PyCFunction)Strgrp_grp_for, (METH_VARARGS | METH_KEYWORDS),
        "Find a cluster for a string, if one exists" },
    { "grp_exact", (PyCFunction)Strgrp_grp_exact,
        (METH_VARARGS | METH_KEYWORDS), "Find group by exact match" },
    { "grps_for", (PyCFunction)Strgrp_grps_for, (METH_VARARGS | METH_KEYWORDS),
        "Provide a tuple of grouops ordered by match score descending" },
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
    "Cluster strings based on longest common subsequence",
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

    GrpType.tp_new = &PyType_GenericNew;
    if (PyType_Ready(&GrpType) < 0) {
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
