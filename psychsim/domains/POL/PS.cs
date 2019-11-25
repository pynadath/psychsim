using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System;
using TSS;

namespace PsychSim
{

    public  class PS${name} : PSCivilian
    {


        // Start is called before the first frame update
        void Start()
        {
            ID = "${name}";
        }

// Update is called once per frame
        void Update()
        {
            if (bHourHasTicked)
            {
                update_comfort();
                update_health();
                update_wealth();
                update_hunger();

                chooseAction();
                bHourHasTicked = false;

            }

        }


${dynamics}

        void chooseAction()
        {
            ${policy}

        }



    }
}