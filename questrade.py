from params import *

import requests as req


'''
* Connector class for interfacing with Questrade API:
* https://www.questrade.com/api/documentation/
'''
class Questrade:
    # self._access_token
    # self._access_token_type
    # self._account
    # self._api_server
    # self._authorized_headers <dict>
    # self._refresh_token
    # self._refresh_token_expires_in
    # self._refresh_token_file

    def __init__(self):

        self._refresh_token_file = open(REFRESH_TOKEN_FILE, 'r+') # TODO = check file exists
        self._refresh_token = self._refresh_token_file.read()
        self._authorize()
        self._account = self._update_account()



    '''
    * Executes get request, returns successful reply as JSON
    * Handles logging and exception handling
    '''
    def _get_as_json(self, api_url, req_params=None, req_headers=None):

        res = req.get(api_url, headers=req_headers, params=req_params)
        res.raise_for_status() # raise exception if not 200 OK

        return res.json()

    '''
    * Get access token and resource server information
    '''
    def _authorize(self):

        req_params = {'grant_type': 'refresh_token', 'refresh_token': self._refresh_token}
        res_json = self._get_as_json(QUESTRADE_OAUTH2_REFRESH_TOKEN_SERVER, req_params=req_params)

        self._access_token = res_json['access_token']
        self._access_token_type = res_json['token_type']
        self._api_server = res_json['api_server']
        self._refresh_token = res_json['refresh_token']
        self._refresh_token_expires_in = res_json['expires_in']
        self._authorized_headers = {
            'Host': self._api_server, 
            'Authorization': self._access_token_type + ' ' + self._access_token
            }
        
        self._save_refresh_token()
        return


    '''
    * Write new refresh_token to file
    '''
    def _save_refresh_token(self):
        try:
            self._refresh_token_file.seek(0) 
            self._refresh_token_file.write(self._refresh_token)
            self._refresh_token_file.truncate()
            self._refresh_token_file.close() 
        except:
            print("error writing to refresh token file")
        return


    '''
    * Uses API to get account number and populates _Account object
    * 
    * For the purpose of this API's implementation, there is only
    * a single account expected per user though this may be expanded 
    * in the future
    '''
    def _update_account(self):

        num = self._get_account_number()
        balances = self._get_account_balances(num)
        positions = self._get_account_positions(num)

        accnt = self._Account(num, balances['cash'], balances['total_equity'], positions)
        return accnt


    def _get_account_number(self):
        res_json = self._get_as_json(self._api_server + 'v1/accounts', 
            req_headers=self._authorized_headers)

        return res_json['accounts'][0]['number']


    def _get_account_balances(self, acc_num):
        res_json = self._get_as_json(self._api_server + 'v1/accounts/' + acc_num + '/balances', 
            req_headers=self._authorized_headers)
        
        for balance in res_json['perCurrencyBalances']:
            if balance['currency'] == 'CAD':
                return {
                    'cash': balance['buyingPower'], 
                    'total_equity': balance['totalEquity']
                }

        raise Exception #TODO - specific


    def _get_account_positions(self, acc_num):
        res_json = self._get_as_json(self._api_server + 'v1/accounts/' + acc_num + '/positions', 
            req_headers=self._authorized_headers)

        positions = {}
        for pos in res_json['positions']:
            ticker = pos['symbol']
            current_price = pos['currentPrice']
            num_shares = pos['openQuantity']
            positions[ticker] = Position(ticker, current_price, num_shares)

        return positions

    '''
    * Data Object representing the account of the resource owner
    * Comprising of data of balances and positions held
    *
    * This class is immutable, it holds data of an 
    * account at a particular instance in time to avoid calls to API
    * In the future there may be several accounts per user
    '''
    class _Account:

        # self.account_number
        # self.cash
        # self.total_equity
        # self.positions <ticker:Position dict>

        def __init__(self, account_number, cash, total_equity, positions):
            self.account_number = account_number
            self.cash = cash
            self.total_equity = total_equity
            self.positions = positions


    # Interface Methods
    # if considerable amount of time passed - update account, else use cached values

    '''
    * Get the amount of cash (buying power) in the account
    '''
    def get_cash(self):
        return self._account.cash


    def get_total_equity(self):
        return self._account.total_equity


    def get_positions(self):
        return self._account.positions


'''
* Represents the most recent status of a position ie. VEE.TO
'''
class Position:

    # self.ticker
    # self.current_price
    # self.num_shares

    def __init__(self, ticker, current_price, num_shares):
            self.ticker = ticker
            self.current_price = current_price
            self.num_shares = num_shares