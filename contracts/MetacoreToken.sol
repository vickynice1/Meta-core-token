// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract MetacoreToken {
    string public name = "Metacore Token";
    string public symbol = "META";
    uint8 public decimals = 18;
    uint256 public totalSupply = 1000000 * 10**decimals;
    
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    
    address public owner;
    
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    event ContractDeployed(address indexed contractAddress, address indexed deployer, uint256 timestamp);
    
    constructor() {
        owner = msg.sender;
        balanceOf[msg.sender] = totalSupply;
        emit Transfer(address(0), msg.sender, totalSupply);
        emit ContractDeployed(address(this), msg.sender, block.timestamp);
    }
    
    function transfer(address to, uint256 value) public returns (bool) {
        require(balanceOf[msg.sender] >= value, "Insufficient balance");
        balanceOf[msg.sender] -= value;
        balanceOf[to] += value;
        emit Transfer(msg.sender, to, value);
        return true;
    }
    
    function approve(address spender, uint256 value) public returns (bool) {
        allowance[msg.sender][spender] = value;
        emit Approval(msg.sender, spender, value);
        return true;
    }
    
    function transferFrom(address from, address to, uint256 value) public returns (bool) {
        require(balanceOf[from] >= value, "Insufficient balance");
        require(allowance[from][msg.sender] >= value, "Insufficient allowance");
        
        balanceOf[from] -= value;
        balanceOf[to] += value;
        allowance[from][msg.sender] -= value;
        
        emit Transfer(from, to, value);
        return true;
    }
    
    function mint(address to, uint256 value) public {
        require(msg.sender == owner, "Only owner can mint");
        totalSupply += value;
        balanceOf[to] += value;
        emit Transfer(address(0), to, value);
    }
    
    function getContractInfo() public view returns (string memory, string memory, uint256, address) {
        return (name, symbol, totalSupply, owner);
    }
}
