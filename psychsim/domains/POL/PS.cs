using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System;
using TSS;

namespace PsychSim
{

    public  class PS${name} : MonoBehaviour
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
        protected virtual void HandleHurricane()
        {

        }
        protected virtual void RaiseActionChangedEvent(ActionChangedEventArgs eventArgs)
        {
            if (ActionChanged != null)
                ActionChanged.Invoke(this, eventArgs);
        }


    }
}