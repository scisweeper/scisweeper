#!/bin/bash
awk '{ print $1+$2*$3 }1{print 1}' input_file > output.log