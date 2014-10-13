#include <Python.h>
#include <string.h>
#include <stdint.h>
#include <stdio.h>

static inline int rmindex(int r, int i, int j) {
    return r * i + j;
}

static int16_t
lcs(const char * const a, const char * const b) {
    const int la = strlen(a);
    const int lap1 = la + 1;
    const int lb = strlen(b);
    const int lbp1 = lb + 1;
    int16_t * const lookup = calloc(lbp1 * 2, sizeof(uint16_t));
    if (!lookup) {
        return -1;
    }
    int ia, ib;
    for (ia = la - 1; ia >= 0; ia--) {
        for (ib = lb - 1; ib >= 0; ib--) {
            if (a[ia] == b[ib]) {
                lookup[rmindex(lbp1, ia & 1, ib)] =
                    1 + lookup[rmindex(lbp1, (ia + 1) & 1, ib + 1)];
            } else {
                const int16_t ap1b = lookup[rmindex(lbp1, (ia + 1) & 1, ib)];
                const int16_t abp1 = lookup[rmindex(lbp1, ia & 1, ib + 1)];
                lookup[rmindex(lbp1, ia & 1, ib)] = (ap1b > abp1) ? ap1b : abp1;
            }
        }
    }
    int16_t result = lookup[0];
    free(lookup);
    return result;
}

static PyObject *
py_lcs(PyObject *self, PyObject *args) {
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

/*
int main(void) {
    const char * const a = "ANZ ATM WILLUNGA 10 HIGH ST      WILLUNGA     SA";
    const char * const b = "CARD ENTRY AT MAWSON LAKES BRANCH";
    printf("lcs: %d\n", lcs(a, b));
    return 0;
}
*/

static PyMethodDef LcsMethods[] = {
    {"lcs", py_lcs, METH_VARARGS, "Longest Common Subsequence"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef LcsModule = {
    PyModuleDef_HEAD_INIT,
    "lcs",
    NULL,
    -1,
    LcsMethods
};

PyMODINIT_FUNC
PyInit_lcs(void) {
    return PyModule_Create(&LcsModule);
}
