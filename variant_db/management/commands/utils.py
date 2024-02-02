#!/usr/bin/env python

def enumerate_chromosome(chrom):
    if chrom == "X":
        return 23
    elif chrom == "Y":
        return 24
    elif chrom == "M":
        return 25
    else:
        return chrom

def subset_row(row: dict, *desired_keys) -> dict:
    return {k: row[k] for k in desired_keys}

def rename_key(dict_obj: dict, old_name=str, new_name=str) -> dict:
    dict_obj[new_name] = dict_obj[old_name]
    del(dict_obj[old_name])
    return dict_obj