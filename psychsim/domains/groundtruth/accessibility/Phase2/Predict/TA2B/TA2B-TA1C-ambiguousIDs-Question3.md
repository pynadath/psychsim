# Specific question #


The Phase2_Predict_IDP contains non-unique actor identifiers within the pre surveys.


For example within the file, Instances/Instance18/Runs/run-0/RunDataTable.tsv, there are Pre-Hurricane survey reports that all correspond to the EntityIdx ‘ActorPre 1’. However, the survey responses on time-steps 8, 22, 35, 47, 61, and 72 are all clearly different people as the genders, religion, ethnicity and ages of all of these actors labeled ‘ActorPre 1’ do not match. This issue exists for post-hurricane actor ids such as ‘ActorPost 1’ and so on as well. We were under the understanding that within the pre-surveys actors had unique IDs and within the post-surveys actors have unique IDs. 


Could you confirm whether the IDs have been assigned correctly in the Predict IDP?


For convenience, we have pasted the data from the described example for ‘ActorPre 1’ below.
        {[ 8]}        {'Gender'               }        {'ActorPre 1'}        {'female'  }        {1×1 missing}
        {[ 8]}        {'Age'                  }        {'ActorPre 1'}        {[          39]}        {1×1 missing}
        {[ 8]}        {'Ethnicity'            }        {'ActorPre 1'}        {'minority'}        {1×1 missing}
        {[ 8]}        {'Religion'             }        {'ActorPre 1'}        {'minority'}        {1×1 missing}
        {[ 8]}        {'Children'             }        {'ActorPre 1'}        {[           2]}        {1×1 missing}
        {[ 8]}        {'Fulltime Job'         }        {'ActorPre 1'}        {'yes'         }        {1×1 missing}
        {[ 8]}        {'Pets'                 }        {'ActorPre 1'}        {'yes'         }        {1×1 missing}
        {[ 8]}        {'Wealth'               }        {'ActorPre 1'}        {[           7]}        {1×1 missing}
        {[ 8]}        {'Residence'            }        {'ActorPre 1'}        {'Region15'}        {1×1 missing}
        {[ 8]}        {'ActorPre At She…'}        {'ActorPre 1'}        {'no'          }        {1×1 missing}
        {[ 8]}        {'ActorPre Evacua…'}        {'ActorPre 1'}        {'no'          }        {1×1 missing}
        {[ 8]}        {'ActorPre Category'}        {'ActorPre 1'}        {[           2]}        {1×1 missing}
        {[ 8]}        {'ActorPre Antici…'}        {'ActorPre 1'}        {[           1]}        {1×1 missing}
        {[ 8]}        {'ActorPre Antici…'}        {'ActorPre 1'}        {[           2]}        {1×1 missing}
        {[ 8]}        {'ActorPre Risk'        }        {'ActorPre 1'}        {[           6]}        {1×1 missing}
        {[22]}        {'Gender'               }        {'ActorPre 1'}        {'female'  }        {1×1 missing}
        {[22]}        {'Age'                  }        {'ActorPre 1'}        {[          38]}        {1×1 missing}
        {[22]}        {'Ethnicity'            }        {'ActorPre 1'}        {'majority'}        {1×1 missing}
        {[22]}        {'Religion'             }        {'ActorPre 1'}        {'majority'}        {1×1 missing}
        {[22]}        {'Children'             }        {'ActorPre 1'}        {[           2]}        {1×1 missing}
        {[22]}        {'Fulltime Job'         }        {'ActorPre 1'}        {'yes'         }        {1×1 missing}
        {[22]}        {'Pets'                 }        {'ActorPre 1'}        {'yes'         }        {1×1 missing}
        {[22]}        {'Wealth'               }        {'ActorPre 1'}        {[           7]}        {1×1 missing}
        {[22]}        {'Residence'            }        {'ActorPre 1'}        {'Region12'}        {1×1 missing}
        {[22]}        {'ActorPre At She…'}        {'ActorPre 1'}        {'no'          }        {1×1 missing}
        {[22]}        {'ActorPre Evacua…'}        {'ActorPre 1'}        {'yes'         }        {1×1 missing}
        {[22]}        {'ActorPre Category'}        {'ActorPre 1'}        {[           4]}        {1×1 missing}
        {[22]}        {'ActorPre Antici…'}        {'ActorPre 1'}        {[           2]}        {1×1 missing}
        {[22]}        {'ActorPre Antici…'}        {'ActorPre 1'}        {'N/A'         }        {1×1 missing}
        {[22]}        {'ActorPre Risk'        }        {'ActorPre 1'}        {[           1]}        {1×1 missing}
        {[35]}        {'Gender'               }        {'ActorPre 1'}        {'male'        }        {1×1 missing}
        {[35]}        {'Age'                  }        {'ActorPre 1'}        {[          70]}        {1×1 missing}
        {[35]}        {'Ethnicity'            }        {'ActorPre 1'}        {'majority'}        {1×1 missing}
        {[35]}        {'Religion'             }        {'ActorPre 1'}        {'minority'}        {1×1 missing}
        {[35]}        {'Children'             }        {'ActorPre 1'}        {[           0]}        {1×1 missing}
        {[35]}        {'Fulltime Job'         }        {'ActorPre 1'}        {'yes'         }        {1×1 missing}
        {[35]}        {'Pets'                 }        {'ActorPre 1'}        {'no'          }        {1×1 missing}
        {[35]}        {'Wealth'               }        {'ActorPre 1'}        {[           7]}        {1×1 missing}
        {[35]}        {'Residence'            }        {'ActorPre 1'}        {'Region11'}        {1×1 missing}
        {[35]}        {'ActorPre At She…'}        {'ActorPre 1'}        {'yes'         }        {1×1 missing}
        {[35]}        {'ActorPre Evacua…'}        {'ActorPre 1'}        {'no'          }        {1×1 missing}
        {[35]}        {'ActorPre Category'}        {'ActorPre 1'}        {[           1]}        {1×1 missing}
        {[35]}        {'ActorPre Antici…'}        {'ActorPre 1'}        {'N/A'         }        {1×1 missing}
        {[35]}        {'ActorPre Antici…'}        {'ActorPre 1'}        {[           2]}        {1×1 missing}
        {[35]}        {'ActorPre Risk'        }        {'ActorPre 1'}        {[           2]}        {1×1 missing}
        {[47]}        {'Gender'               }        {'ActorPre 1'}        {'male'        }        {1×1 missing}
        {[47]}        {'Age'                  }        {'ActorPre 1'}        {[          68]}        {1×1 missing}
        {[47]}        {'Ethnicity'            }        {'ActorPre 1'}        {'majority'}        {1×1 missing}
        {[47]}        {'Religion'             }        {'ActorPre 1'}        {'majority'}        {1×1 missing}
        {[47]}        {'Children'             }        {'ActorPre 1'}        {[           0]}        {1×1 missing}
        {[47]}        {'Fulltime Job'         }        {'ActorPre 1'}        {'yes'         }        {1×1 missing}
        {[47]}        {'Pets'                 }        {'ActorPre 1'}        {'yes'         }        {1×1 missing}
        {[47]}        {'Wealth'               }        {'ActorPre 1'}        {[           7]}        {1×1 missing}
        {[47]}        {'Residence'            }        {'ActorPre 1'}        {'Region07'}        {1×1 missing}
        {[47]}        {'ActorPre At She…'}        {'ActorPre 1'}        {'no'          }        {1×1 missing}
        {[47]}        {'ActorPre Evacua…'}        {'ActorPre 1'}        {'no'          }        {1×1 missing}
        {[47]}        {'ActorPre Category'}        {'ActorPre 1'}        {[           3]}        {1×1 missing}
        {[47]}        {'ActorPre Antici…'}        {'ActorPre 1'}        {[           1]}        {1×1 missing}
        {[47]}        {'ActorPre Antici…'}        {'ActorPre 1'}        {[           2]}        {1×1 missing}
        {[47]}        {'ActorPre Risk'        }        {'ActorPre 1'}        {[           7]}        {1×1 missing}
        {[61]}        {'Gender'               }        {'ActorPre 1'}        {'female'  }        {1×1 missing}
        {[61]}        {'Age'                  }        {'ActorPre 1'}        {[          67]}        {1×1 missing}
        {[61]}        {'Ethnicity'            }        {'ActorPre 1'}        {'majority'}        {1×1 missing}
        {[61]}        {'Religion'             }        {'ActorPre 1'}        {'majority'}        {1×1 missing}
        {[61]}        {'Children'             }        {'ActorPre 1'}        {[           0]}        {1×1 missing}
        {[61]}        {'Fulltime Job'         }        {'ActorPre 1'}        {'no'          }        {1×1 missing}
        {[61]}        {'Pets'                 }        {'ActorPre 1'}        {'no'          }        {1×1 missing}
        {[61]}        {'Wealth'               }        {'ActorPre 1'}        {[           1]}        {1×1 missing}
        {[61]}        {'Residence'            }        {'ActorPre 1'}        {'Region03'}        {1×1 missing}
        {[61]}        {'ActorPre At She…'}        {'ActorPre 1'}        {'yes'         }        {1×1 missing}
        {[61]}        {'ActorPre Evacua…'}        {'ActorPre 1'}        {'no'          }        {1×1 missing}
        {[61]}        {'ActorPre Category'}        {'ActorPre 1'}        {[           3]}        {1×1 missing}
        {[61]}        {'ActorPre Antici…'}        {'ActorPre 1'}        {'N/A'         }        {1×1 missing}
        {[61]}        {'ActorPre Antici…'}        {'ActorPre 1'}        {[           3]}        {1×1 missing}
        {[61]}        {'ActorPre Risk'        }        {'ActorPre 1'}        {[           1]}        {1×1 missing}
        {[72]}        {'Gender'               }        {'ActorPre 1'}        {'female'  }        {1×1 missing}
        {[72]}        {'Age'                  }        {'ActorPre 1'}        {[          27]}        {1×1 missing}
        {[72]}        {'Ethnicity'            }        {'ActorPre 1'}        {'minority'}        {1×1 missing}
        {[72]}        {'Religion'             }        {'ActorPre 1'}        {'minority'}        {1×1 missing}
        {[72]}        {'Children'             }        {'ActorPre 1'}        {[           0]}        {1×1 missing}
        {[72]}        {'Fulltime Job'         }        {'ActorPre 1'}        {'yes'         }        {1×1 missing}
        {[72]}        {'Pets'                 }        {'ActorPre 1'}        {'yes'         }        {1×1 missing}
        {[72]}        {'Wealth'               }        {'ActorPre 1'}        {[           7]}        {1×1 missing}
        {[72]}        {'Residence'            }        {'ActorPre 1'}        {'Region07'}        {1×1 missing}
        {[72]}        {'ActorPre At She…'}        {'ActorPre 1'}        {'no'          }        {1×1 missing}
        {[72]}        {'ActorPre Evacua…'}        {'ActorPre 1'}        {'no'          }        {1×1 missing}
        {[72]}        {'ActorPre Category'}        {'ActorPre 1'}        {[           4]}        {1×1 missing}
        {[72]}        {'ActorPre Antici…'}        {'ActorPre 1'}        {[           1]}        {1×1 missing}
        {[72]}        {'ActorPre Antici…'}        {'ActorPre 1'}        {[           2]}        {1×1 missing}
        {[72]}        {'ActorPre Risk'        }        {'ActorPre 1'}        {[           7]}        {1×1 missing}


# Other applicable details #




# Answer #

The IDs are unique within each hurricane. We can provide a different ID encoding if preferred.