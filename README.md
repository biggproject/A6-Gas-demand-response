# Application A6: Gas Demand-Response

The goal of Application A6 is to develop a demand response (DR) scheme exploiting gas flexibility in space heating for
residential complex. Gas providers can avoid additional costs or CO2 emissions by letting customers play an active role
in DR, thereby restoring the balance between supply and demand. The flexible assets used in this project for providing
DR are gas-based domestic hot water boilers used for residential hot water and heating. The objective of the pilot is to
meet a targeted gas consumption level. This is done to optimize energy efficiency and minimize gas usage, resulting in
cost savings and reduced environmental impact. The pilot achieves this objective by jointly controlling the gas
consumption of multiple boilers, ensuring they operate collectively to meet the target consumption. When controlling,
the comfort of the user must be taken into account: the house may not cool down or warm up too far from the thermostat
temperature. The cost deviations of additional heating or cooling (compared to normal consumption) also play a role. For
example, with a high target consumption (where several boilers will be activated), ideally boilers are activated first
whose heat demand was already expected for a later moment.
We utilize a reinforcement learning (RL) approach to develop a demand response controller policy. The RL agent learns
from historical and/or simulated data to determine optimal actions based on the input raw data. The learned policy is
then applied in real-world scenarios to implement the demand response strategy. The specific decisions made by the
policy depend on the input data and the objectives of the demand response, such as adjusting the operation of boilers to
meet target gas consumption or optimizing energy usage in response to changing conditions. The pipeline in the figure
below shows the flow of raw data, that is used to learn an RL agent that implements the DR.

![RL pipeline](./figures/flowchart.png)

## Technical solution as a pipeline

Training the RL policy necessitates the definition of an agent and an environment. The environment is defined as
real-world environment, a household, that translates an action (heating / no heating) into new state at every time-step.
The agent is the entity that takes the actions, which consist of disabling or enabling the room heating. Enabling
results in an increasing room temperature and an immediate consumption of gas usage; disabling sets the gas consumption
to zero, and slowly declines the room temperature. The reward is defined as the immediate gas consumption given an
action is taken. As gas consumption in kWh is not given, we use a modulation level (power percentage of total gas boiler
power) as proxy. We refer to the RL-Training documentation on GitHub (link) for more details about the state, action and
reward definition.
In this deliverable, we focus on modelling flexibility, which is expressed as preponing or postponing heating actions
against a cost. Here, the cost is the accumulative gas consumption over the period (e.g., 24 hours) after the taken
action. An offline model-free RL-approach is used to estimate this cost. Historical heating actions and temperature and
gas usage parameters are used to train the RL-agent. As each household has different heating demands and parameters,
there will be an RL-agent for each household.
RL-agent inputs: historical residential data collected per household including:

- Timestamp (DD/MM/YY hh:mm:ss),
- Gas consumption/modulation,
- Room temperature/Boiler temperature,
- Boiler set points,
- Outside temperature, and,
- Room temperature set points.
- Proposed action (heating/no heating)
  Outputs:
- Estimated gas consumption of upcoming configurable horizon-period (set to 24 hours)

The pipeline comprises periodic processes, such as retrieving the latest measurement data and training an RL-agent.
Other processes are executed when a DR-event is triggered. Both types of processes are listed and explained next.

**Periodically** (e.g., every hour or every day)**:**

- Retrieving (real-time) measurement data required for training a RL-agent, or for monitoring during DR events.
  Typically, during business-as-usual (when there is no ongoing DR-event), the data retrieval interval can be lower than
  during a DR-event, where a higher measurement frequency is desired for fine observation of power values.
- Training a reinforcement learning agent (policy evaluation). An agent is trained separately for each household. This
  agent can provide a prediction of the accumulative energy consumption for the next horizon (e.g., 24 hours) at any
  time
  of the day, given the activity of the boiler and a set of properties, including internal boiler temperatures, the
  thermostat temperature and indoor/outside temperature.

**During DR events:**

- Using the reinforcement learning agent (inference) to predict the expected gas consumption. In addition, the target
  consumption is calculated that is aimed for during the DR event.
- Participating boilers are ranked on the highest expected gas savings, which is calculated by the outputs of the RL
  agents. To be more concise, from each agent the expected gas consumption difference is calculated between the default
  -business as usual- action and the proposed action. This value is also called the advantage value. The proposed action
  depends on the DR-objective: upwards DRs have proposed action ‘heating’ and downwards DRs have action ‘no heating’. In
  other words, for downward DR events, the expected savings equals taking an alternative (proposed) action instead of
  the action that would otherwise would have happened. The expected gas savings are calculated while comfort constraints are
  considered. The comfort limits in the pilot are set at a maximum (negative and positive) deviation of 1 degree Celsius
  from the thermostat temperature. A separate entity, called the ‘action-coordinator’ gathers all agents and calculates the expected savings for each
  household, after which it ranks each household based on the advantage value from low to high. A low (negative)
  advantage value means a high saving. The households that have the highest expected savings are selected first when a DR event is
  triggered, after which additional (less economic viable households) are activated one-by-one if the current set of
  households does not suffice in the DR-response.
- The continuous sending of boiler commands, so that the actual consumption approaches the target consumption as closely
  as possible. A proportional integral (PI) controller is used to control a discrete value that determines the number of
  participating boilers and the magnitude of the actions.
- Monitoring the observed boiler values on an online platform. This platform also shows an indication of how much
  flexibility is being ‘used’ at any moment of time during a DR event, by measuring how many households are activated.

## Implementation

The solution is implement as two independent entities: one is the RL-agent and the other is the action-coordinator.
The RL-agent is a Python program that is executed periodically (e.g., every hour) to train the agent. The
action-coordinator is program that sends commands and reads out the statuses of the individual boilers.

### RL-training
==============================
The RL-agents are designed using a policy evaluation setting using the fitted-Q iteration algorithm. For this, each household is modeled as an MDP with the following:

#### States
The states are defined to based on the assumption that a single houshold can be modelled as a partially observable 
Markov Decision process. To provide the agent with sufficient, _causal_ information, we use the following features:

    - time (t)
    - Outside Air Temperature (t_out)
    - Room Temperature Setpoint (t_r_set)
    - Past Room Temperatures  ([t_r,t-k, ..., t_r,t-1])
    - Past Boiler Modulations ([b_m,t-k, ..., b_r,t-1])
    - Current Room Temperature (t_r)

The value of k (referred to as _depth_) is dependent on the data frequency and is set such that the state comprises information from the past 4 
hours. (for frequency of 5 mins, k=48)

time is int between 0 and 1440, multiples of 5.

#### Actions
The actions are assumed to be boiler setpoint values that are transformed into boolean ON/ OFF values.  The threshold 
for this is set to 20°C, implying any value above this leads to action ON (1) and setpoint value below this is considered 
as action OFF (0).

####  Rewards
The instantaneous rewards are modelled as the boiler modulation at the current instant (b_m,t). Any Q-function trained 
using this reward leads to a value corresponding to the cumulative gas consumption of that house. 

#### Algorithm
To train the agents, the fitted Q-iteration algorithm is used. 

To provide additional stability, we follow an ensemble-based approach called meanQ, which uses a set of N function approximators
per iteration (can be set using _-es_) and computes the mean value of their prediction for calculating the Q-value. 

Additionally, because we use neural networks as functional approximators, the obtained data must be scaled before the 
regression step. To enable proper scaling for different houses, we use the [transformation_class](./src/rl_agents/utils/data_transformations.py)
This takes as input the house_id and produces a transformation object that can be used by the agent for all scaling and
re-scaling operations. 

#### Outputs
This repository is used for training the RL agents. Once training is done, the models are saved in the agent directory 
as ``models.pkl``. 


### Action Coordinator

==================

#### Installing packages

Working with poetry, first install poetry on your local machine.

- [poetry installation](https://python-poetry.org/docs/#installation)

Add packages with following command:

    poetry add <package-name>

You can also specify specific version etc. More information on
the [poetry site](https://python-poetry.org/docs/cli/#add).

Run in own environment:

    py -m poetry shell

#### Documentation

The hexagon structure of the service can be seen on the picture below.
This is a first version.

![Hexagon sturcture action coordinator](./action_coordinator/images/hexagon-structure.drawio.png)

#### Configuration

The file 'config.yaml' contains the configuration for the service. The file is located in the root of the project.
This section describes the configuration options.

- bau_controller:
    - control_interval_s: The interval in seconds to send out new actions to each device, during Business-As-Usual.
- dr_event:
    - participants: The list of houses that are participating in the DR event.
    - control_interval_s:  The interval in seconds to send out new actions to each device.
- pi_controller:
    - kp: The proportional gain of the PI controller. More information in section 'PI controller'.
    - ki: The integral gain of the PI controller. More information in section 'PI controller'.
- agent:
    - trajectory_length: The length of the trajectory in seconds, used for shaping the input data for the Q-agent.
    - trajectory_interval_s: The interval in seconds to send out new actions to each device, during a DR-event.
    - action_space: The action space of the Q-agent.
- action_dispatcher:
    - enable_dispatch_actions: 1 to enable the action dispatcher, 0 to disable. A disabled action dispatcher results in
      dummy action coordinator, where all the actions are calculated but not sent out to the devices.
    - enable_backup_controller: 1 to enable the backup controller, 0 to disable. A disabled backup controller will not
      send out any actions to the devices.
    - temperature_band: The temperature band in which the backup controller will send out actions.
- house_id_mappings:
    - 'internal':'external': Maps the house id to use internally (logs/ database) to the house id used in the API
      controller (e.g. "House_1: boiler_id_a8:03:2a:4a:35:d0")
- action_mappings:
    - default: The default action mapping for the setpoint action.
    - 'internal':'external': Maps the action to use internally (logs/ database) to the action used in the API controller

#### Control States

We briefly touch on the two states the action coordinator can be in:

1. Business-As-Usual (BAU): The action coordinator is in BAU when there is no DR event active. The action coordinator
   will send out actions to the devices every x seconds, where x is defined in the configuration file, please
   see `bau_controller`→`control_interval_s`. At the moment, the actions are binary, either 0 or 1, corresponding to '
   off' and 'on'. When `t_r` is below `t_r_set`, the action is 1, otherwise the action is 0 for a given household.
2. DR event: The action coordinator is in a DR event when there is a DR event active. The action coordinator will send
   out actions to the devices every x seconds, where x is defined in the configuration file, please
   see `dr_event`→`control_interval_s`. The actions that are sent out are a direct result of the response level. A list
   of actions for each response level is defined at the start of each DR event. A PI-Control is used to control the
   response level, which would increase of the power usage is too low, or decrease if the power usage is too high.

So in both states, the action coordinator will send out actions to the devices. The action coordinator will calculate
the actions based on the current state of the devices. After, it sends out the actions to the devices using the boiler
aggregator API.

#### PI controller

The PI controller is used to control the response level during a DR event, and is adjustable by its ki and kp gains.
In its current state, the PI controller is adjusted to an expected situation during the field test, described below:

At February 2nd, 2023, at 9:30 am, the following data is captured: the boiler modulation for all 5 trial households, for
the last 24 hours. After, the max modulation level at 'on'-times during the 24 hours was defined:

| House    | Boiler modulation |
|----------|-------------------|
| House_2  | 78                |
| House_9  | 82                |
| House_13 | 78                |
| House_38 | 90                |
| House_42 | 65                |

After, a DR event is simulated on 5 simple boiler emulators. Whenever a boiler receives an 'on' action, it will have a
boiler modulation of the corresponding value in the table; at 'off' times, the boiler modulation will be 0.

The DR event is launched for a power reduction of `-50` for a duration of 15 minutes. The PI controller is visually
tuned
(ad-hoc) to get a result, as shown below. Note that we speeded up the test by 10 times. The actual test took 900 seconds
instead of the 90 seconds that is shown in the graph.

![DR response of 15 minutes over 5 emulated households](./action_coordinator/images/dr_plot.png)

We can observe that after 2 minutes, the response level dropped to negative 1, which induced a fall in observed power
shortly after. Starting from this moment, the PI controller oscilates the response level between 0 and -1 to keep the
observed power around the target power.

The above experiment resulted in the following gains: `kp = 0.01` and `ki = 0.001`.

### Error handling

#### Aggregator API failures

During the pilot, the boiler aggregator API was prone to instability. Therefore, the action coordinator has to be able
to handle
API failures at any time. Before going into the details of the error handling, The way the action coordinator handles
API failures is different for BAU and DR event.

#### BAU

When the action coordinator is in BAU, the action coordinator will send out actions to the devices every x seconds,
where x is defined in the configuration file, please see `bau_controller`→`control_interval_s`. If the API fails, the
action
coordinator will retry to send out the actions **at the next control interval**. In the current setup, the retry will be
done at the next control interval, but this can be changed in the future. The number of retries is infinite, but due to
the relatively long control interval, the number of retries is limited in practice.

#### DR event

When the action coordinator is in a DR event, the action coordinator will send out actions to the devices every x
seconds,
where x is defined in the configuration file, please see `dr_event`→`control_interval_s`. If the API fails, the action
coordinator will retry to send out the actions **at the next control interval**. In the current setup, the retry will be
done at the next control interval, but this can be changed in the future. The number of retries is infinite, but due to
the relatively long control interval, the number of retries is limited in practice.

There is one exception to the above. If the DR has just started, the action coordinator tries to retrieve a trajectory
of multiple measurements from the aggregator API. This request is more demanding than the other requests, as it typically has
multiple hours (12 hours for the trial) of data, with higher change on failure. If this request fails, the DR action
cannot be started, as the action coordinator does not have enough information to calculate the actions. In this case,
the DR event is cancelled, and BaU is started again.
