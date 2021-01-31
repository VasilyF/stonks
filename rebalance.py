#!/usr/bin/env python3

from math import trunc
from questrade import Questrade, Position
#import sys


DEMO_CASH = 3500

# TODO
'''
- define methods as static and class where appropriate
- handle exceptions
- put portfolio weights in csv file
- make params.py into parameters
'''

portfolio_weight = {
    'VIU.TO': 0.225,
    'XUU.TO': 0.3978,
    'VCN.TO': 0.30,
    'VEE.TO': 0.0772
}



def main():
    
    # authorize into resource server
    # provide callback to refresh access token when expired
    api = Questrade()

    # get information on account balances
    cash = api.get_cash() + DEMO_CASH
    equity = api.get_total_equity() + DEMO_CASH

    # get information on account positions
    positions = api.get_positions()

    print("\n")
    print("-------------- PULLED DATA ----------------")
    print(f"cash:\t${cash:.2f}")
    print(f"equity:\t${equity:.2f}\n")
    for t, pos in positions.items():
        print("{} => quantity: {}\t\t price: ${:.2f}".format(t, pos.num_shares, pos.current_price))
    print("-------------------------------------------")
    print("\n")

    # calculate new orders 
    new_orders, cash_rem = calculate_new_orders(cash, equity, positions, portfolio_weight)

    actual_weight = {}
    target_weight = {}

    for pos in positions.values():
        actual_weight[pos.ticker] = (pos.num_shares + new_orders[pos.ticker])*pos.current_price/equity*100
        target_weight[pos.ticker] = portfolio_weight[pos.ticker]*100

    # print to console
    display_result(new_orders, cash_rem, actual_weight, target_weight)
    
    return


'''
* Calculate the number of new shares to buy of each position as follows:
*
* 1. Determine the number of units (truncated) each position should hold - truncated unit allocation (TUA)
*  - If positions already have more units than TUA, no new units bought, current units maintained
*  - Positions that can still have their unit quantities increased (eligible positions) are increased 
*    proportional to their weight normalized with respect to the other eligible positions
*  - A new truncated unit allocation is established for each position (TUA2)
* 2. Remaining cash is to be distributed such as to increase cash utilization amongst the
*    eligible positions (those that are not over-represented)
* 3. Remaining cash is to be distributed such as to increase cash utilization amongst the 
*    over-represented positions
*
* Return tuple: {ticker -> additional units}, remaining cash
'''
def calculate_new_orders(cash, equity, positions, portfolio_weight):

    #TODO - make over_represented into set?
    over_represented = {} # dict (ticker -> position) of over-represented positions
    eligible_portfolio_weight = {}
    eligible_weight = 0 # sum of weight of eligible positions for normalization

    # calculate the truncated unit allocation for each position
    tua = {} # truncated unit allocation 
    for ticker, weight in portfolio_weight.items():
        tua[ticker] = trunc(weight*equity/positions[ticker].current_price)

        # determine over-represented positions
        if tua[ticker] < positions[ticker].num_shares:
            over_represented[ticker] = positions[ticker]
        else:
            eligible_weight += weight
            eligible_portfolio_weight[ticker] = weight


    # determine number of additional shares (truncated) for each position
    if len(over_represented) == 0:
        additional_units = {t:tua[t] - positions[t].num_shares for t in tua.keys()}

    else:
        # construct new portfolio weights for eligible positions
        eligible_portfolio_weight.update((t, w/eligible_weight) for t, w in eligible_portfolio_weight.items())
        additional_units = {} # how many additional units


        # determine additional units for eligible positions
        for ticker, weight in eligible_portfolio_weight.items():
            additional_units[ticker] = trunc(weight*cash/positions[ticker].current_price)

        
        # additional units for over-represented positions is 0
        additional_units.update((t, 0) for t in over_represented.keys())

    
    # find remaining cash
    remaining_cash = cash

    for t, u in additional_units.items():
        remaining_cash -= u*positions[t].current_price

    remain_alloc = allocate_remaining(positions, remaining_cash) #TODO - first allocate for eligible

    # add remaining allocation to additional units - these are the units to buy
    for t in remain_alloc.keys():
        additional_units[t] += remain_alloc[t]
        remaining_cash -= positions[t].current_price

    return (additional_units, remaining_cash)


def allocate_remaining(positions, cash_rem):

    

    best_select = {} # {cash_rem -> selection dict {ticker -> units}}
    max_util = {} # {cash_rem -> max_spent}


    '''
    * returns a dictionary {ticker -> units} of how to spend remaining cash
    * populates best_select and max_util dicts up to case called
    '''
    def get_best_select(cash_rem):
        max_spent = 0
        select = {} # best ticker selection dict

        for pos in positions.values():
            price = trunc(pos.current_price *100)
            ticker = pos.ticker

            if price < cash_rem:
                new_cash_rem = cash_rem - price
                if new_cash_rem in best_select:   
                    # best selection for subcase is known, 
                    # current selection includes extra unit for current ticker
                    curr_select = best_select[new_cash_rem]

                else:
                    # subcase not yet solved
                    curr_select = get_best_select(new_cash_rem)

                # update curr_select to increment current position ticker
                if ticker in curr_select:
                    curr_select[ticker] += 1    # previously included in selection
                else:
                    curr_select[ticker] = 1     # new inclusion in selection
                
                # current max is max of subcase + price of ticker
                curr_max = max_util[new_cash_rem] + price

                
                # check if new global max
                if curr_max > max_spent:
                        select = curr_select
                        max_spent = curr_max
        
        max_util[cash_rem] = max_spent
        best_select[cash_rem] = select

        return select
    
    return get_best_select(trunc(cash_rem*100))


class colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    ENDC = ENDC = '\033[0m'

def display_result(new_orders, cash_rem, actual_weight, target_weight):
    print("--------------- NEW OREDERS ---------------")
    print("FUND \t NEW UNITS \t PORTFOLIO WEIGHT \t TARGET WEIGHT \n")
    for ticker, new_units in new_orders.items():
        print(f"{colors.CYAN}{ticker}{colors.ENDC} \t {colors.GREEN}{new_units}{colors.ENDC} \t\t {actual_weight[ticker]:.2f}%    \t\t {target_weight[ticker]:.2f}%")
    print("-------------------------------------------")
    print(f"Remaining cash: ${cash_rem:.2f}")
    print("\n")


if __name__ == '__main__':
    main()