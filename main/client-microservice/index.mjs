import { Command } from 'commander';
import inquirer from 'inquirer';
import fs from 'fs';
import axios from "axios"


  const program = new Command();
  program.name('CLI').description('CLI for DOS Project').version('1.0.0');
  let questionSearch = [
    {
      type: 'input',
      name: 'bookTitle',
      message: 'please enter book topic to get details about it: ',
    },
  ];

  let questionInfo=[{
    type: 'number',
    name: 'itemNumber',
    message: 'please enter items number to get info about it: ',
  },]

  let questionPurchase = [{
    type: 'number',
    name: 'itemNumber',
    message: 'please enter book item number to purchase it: ',
  },
  {
    type: 'number',
    name: 'money',
    message: 'Enter amount of money to pay:  ',
  },
]
  
  program
    .command('search-book-title')
    .alias('s')
    .description('search about specific book using book topic')
    .action(() => {
      inquirer
        .prompt(questionSearch)
        .then(async (answers) => {
          try {
            const result = await axios.get(`http://localhost:8080/catalog-server/search/${answers.bookTitle}`);
            console.log('Response Data:', result.data);
          } catch (error) {
            console.error('Error during request:', error.message);
          }

        })
        .catch((error) => {
          if (error.isTtyError) {
            // Prompt couldn't be rendered in the current environment
          } else {
            // Something else went wrong
          }
        });
    });
  
    program
    .command('info-book-item-number')
    .alias('i')
    .description('info about specific book using item number')
    .action(() => {
      inquirer
        .prompt(questionInfo)
        .then(async (answers) => {
          try {
            const result = await axios.get(`http://localhost:8080/catalog-server/info/${answers.itemNumber}`);
            console.log('Response Data:', result.data);
          } catch (error) {
            console.error('Error during request:', error.message);
          }
        })
        .catch((error) => {
          if (error.isTtyError) {
            // Prompt couldn't be rendered in the current environment
          } else {
            // Something else went wrong
          }
        });
    });
    
    program
    .command('purchase-book-by-item-number')
    .alias('p')
    .description('purchase specific book using item number')
    .action(() => {
      inquirer
        .prompt(questionPurchase)
        .then(async (answers) => {
          // console.log(answers)
          // console.log(answers.purchase)
            try {
              const result = await axios.post(`http://localhost:8080/order-server/purch`,{id:answers.itemNumber,orderCost:answers.money})
              console.log('Response Data:', result.data);
            } catch (error) {
              console.error('Error during request:', error.message);
            }
        })
        .catch((error) => {
          if (error.isTtyError) {
            // Prompt couldn't be rendered in the current environment
          } else {
            // Something else went wrong
          }
        });
    });
  
  program.parse();