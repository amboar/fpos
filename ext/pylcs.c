#include <Python.h>
#include "lcs.h"

static PyObject *
pylcs(PyObject *self, PyObject *args) {
    const char *a, *b;
    if (!PyArg_ParseTuple(args, "ss", &a, &b)) {
        return NULL;
    }
    const int16_t result = lcs(a, b);
    if (-1 == result) {
        return PyErr_NoMemory();
    }
    return PyLong_FromLong(result);
}

static PyMethodDef PyLcsMethods[] = {
    {"pylcs", pylcs, METH_VARARGS, "Longest Common Subsequence"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef PyLcsModule = {
    PyModuleDef_HEAD_INIT,
    "pylcs",
    NULL,
    -1,
    PyLcsMethods
};

PyMODINIT_FUNC
PyInit_pylcs(void) {
    return PyModule_Create(&PyLcsModule);
}
