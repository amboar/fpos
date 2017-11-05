#include <Python.h>
#include <stdio.h>
#include "genann/genann.h"

typedef struct {
    PyObject_HEAD;
    struct genann *ann;
} GenannObject;

static PyObject *
Genann_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    GenannObject *self = (GenannObject *)type->tp_alloc(type, 0);
    if (self != NULL) {
        self->ann = NULL;
    }
    return (PyObject *)self;
}

static int
Genann_init(GenannObject *self, PyObject *args, PyObject *kwds) {
    int inputs, hidden_layers, hidden, outputs;
    if (!PyArg_ParseTuple(args, "iiii", &inputs, &hidden_layers, &hidden,
                &outputs)) {
        return -1;
    }
    self->ann = genann_init(inputs, hidden_layers, hidden, outputs);
    if (!self->ann) {
        return -1;
    }
    return 0;
}

static inline ssize_t
max(ssize_t a, ssize_t b) {
    return a >= b ? a : b;
}

static double *
unpack_PyList(PyObject *listobj, ssize_t n_elems) {
    double *inputs;
    ssize_t len;
    int i;

    len = PyList_Size(listobj);
    inputs = calloc(max(n_elems, len), sizeof(*inputs));
    if (!inputs) {
        void *ret = PyErr_NoMemory();
        return ret;
    }

    for (i = 0; i < len; i++) {
        PyObject *floatobj = PyList_GetItem(listobj, i);
        inputs[i] = PyFloat_AsDouble(floatobj);
    }

    return inputs;
}

static PyObject *
pack_PyList(const double *outputs, ssize_t len) {
    PyObject *listobj;
    int i;

    listobj = PyList_New(0);
    if (!listobj)
        return PyErr_NoMemory();

    for (i = 0; i < len; i++) {
        PyObject *floatobj = PyFloat_FromDouble(outputs[i]);
        if (PyList_Append(listobj, floatobj)) {
            goto cleanup;
        }
    }

    return listobj;

cleanup:
    while(--i >= 0) {
        Py_XDECREF(PyList_GetItem(listobj, i));
    }

    Py_XDECREF(listobj);

    return PyErr_NoMemory();
}

static PyObject *
Genann_run(GenannObject *self, PyObject *args) {
    double const *outputs;
    PyObject *inputsobj;
    double *inputs;

    if (!PyArg_ParseTuple(args, "O", &inputsobj))
        return NULL;

    inputs = unpack_PyList(inputsobj, self->ann->inputs);
    if (!inputs)
        return PyErr_NoMemory();

    outputs = genann_run(self->ann, inputs);
    free(inputs);

    if (!outputs)
        return PyErr_NoMemory();

    return pack_PyList(outputs, self->ann->outputs);
}

static PyObject *
Genann_train(GenannObject *self, PyObject *args, PyObject *kws) {
    char *keywords[] = { "inputs", "outputs", "rate", "iters", NULL };
    PyObject *outputsobj = NULL;
    PyObject *inputsobj = NULL;
    double *outputs;
    double *inputs;
    int iters = 1;
    double rate;
    int i;

    if (!PyArg_ParseTupleAndKeywords(args, kws, "OOd|i", keywords, &inputsobj,
                &outputsobj, &rate, &iters))
        return NULL;

    inputs = unpack_PyList(inputsobj, self->ann->inputs);
    if (!inputs)
        return PyErr_NoMemory();

    outputs = unpack_PyList(outputsobj, self->ann->outputs);
    if (!outputs) {
        free(inputs);
        return PyErr_NoMemory();
    }

    for (i = 0; i < iters; i++) {
        genann_train(self->ann, inputs, outputs, rate);
    }

    free(outputs);
    free(inputs);

    Py_RETURN_NONE;
}

static PyObject *
Genann_read(PyTypeObject *class, PyObject *args) {
    GenannObject *self;
    PyObject *ret;
    genann *ann;
    char *path;
    FILE *f;

    if (!PyArg_ParseTuple(args, "s", &path))
        return NULL;

    f = fopen(path, "r");
    if (!f)
        return PyErr_SetFromErrno(PyExc_OSError);

    ann = genann_read(f);
    if (!ann) {
        ret = PyErr_NoMemory();
        goto cleanup_f;
    }

    self = (GenannObject *)class->tp_new(class, NULL, NULL);
    if (!self) {
        ret = PyErr_NoMemory();
        genann_free(ann);
        goto cleanup_f;
    }

    self->ann = ann;
    ret = (PyObject *)self;

cleanup_f:
    fclose(f);

    return ret;
}

static PyObject*
Genann_write(GenannObject *self, PyObject *args) {
    char *path;
    FILE *f;

    if (!PyArg_ParseTuple(args, "s", &path))
        return NULL;

    f = fopen(path, "w");
    if (!f)
        return PyErr_SetFromErrno(PyExc_OSError);

    genann_write(self->ann, f);

    fclose(f);

    Py_RETURN_NONE;
}

static void
Genann_dealloc(PyObject *obj) {
    GenannObject *self = (GenannObject *)obj;
    genann_free(self->ann);
    Py_TYPE(obj)->tp_free(obj);
}

static PyMethodDef Genann_methods[] = {
    { "run", (PyCFunction)Genann_run, (METH_VARARGS),
        "Runs the feedforward algorithm to calculate the ANN's output" },
    { "train", (PyCFunction)Genann_train, (METH_VARARGS | METH_KEYWORDS),
        "Does a single backprop update" },
    { "read", (PyCFunction)Genann_read, (METH_VARARGS | METH_CLASS),
        "Creates ANN from file saved with write()" },
    { "write", (PyCFunction)Genann_write, (METH_VARARGS), "Saves the ANN" },
    {NULL}
};

static PyTypeObject GenannType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "genann.Genann",           /* tp_name */
    sizeof(GenannObject),      /* tp_basicsize */
    0,                         /* tp_itemsize */
    &Genann_dealloc,           /* tp_dealloc */
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
    "Genann object",           /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    Genann_methods,            /* tp_methods */
    0,                         /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc) &Genann_init,   /* tp_init */
    0,                         /* tp_alloc */
    Genann_new,                /* tp_new */
};

static PyModuleDef GenannModule = {
    PyModuleDef_HEAD_INIT,
    "genann",
    "Feedforward artificial neural network",
    -1,
    NULL, NULL, NULL, NULL, NULL
};

PyMODINIT_FUNC
PyInit_pygenann(void)
{
    PyObject* m;

    if (PyType_Ready(&GenannType) < 0) {
        return NULL;
    }

    m = PyModule_Create(&GenannModule);
    if (m == NULL)
        return NULL;

    Py_INCREF(&GenannType);
    PyModule_AddObject(m, "genann", (PyObject *)&GenannType);
    return m;
}
