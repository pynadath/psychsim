using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System;
using TSS;

namespace PsychSim
{
    public class ActionChangedEventArgs : EventArgs
    {
        public PS${name}ActionEnum mPSAction;
        public PS${name} mPSCivilian;

        public ActionChangedEventArgs(PSCivilian pSCivilian, PSCivilianActionEnum action)
        {
            mPSAction = action;
            mPSCivilian = pSCivilian;
        }
    }


    public enum PS${name}ActionEnum
    {
        ${actions}
    }

    public enum PSEventEnum
    {
        IED,
        Fire,
        BombThreat,
        Hostage,
        Hurricane,
        Curfew,
        Riot
    }

    public  class PS${name} : MonoBehaviour
    {
        ${states}

        protected PS${name}ActionEnum meCurrentAction;
        protected TssPsController mTssPsController;

        // Start is called before the first frame update
        void Start()
        {
            ID = "${name}";
        }

        public void SetController (TssPsController tssPsController)
        {
            mTssPsController = tssPsController;
            mTssPsController.TSSEventOccured += OnTSSEventOccured;

        }
        public event EventHandler<ActionChangedEventArgs> ActionChanged;
        public string ID
        {

            get;
            set;
        }

        public void OnTSSEventOccured(object sender, TSSEventOccuredArgs eventArgs)
        {
#if UNITY_EDITOR
            Debug.Log("TSS Event Occured: " + Enum.GetName(typeof(PSEventEnum), eventArgs.mTSSEvent));
#endif
            switch (eventArgs.mTSSEvent)
            {
                case PSEventEnum.Riot:
                    {

                        HandleRiot();
                        break;
                    }
                case PSEventEnum.Hurricane:
                    {

                        HandleHurricane();
                        break;
                    }
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