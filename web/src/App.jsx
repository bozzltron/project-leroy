/* eslint-disable no-unused-expressions */
import React, { useEffect, useState } from 'react';
import { makeStyles, createStyles } from '@material-ui/core/styles';
import Typography from '@material-ui/core/Typography';
import Grid from '@material-ui/core/Grid';
import visitations from './visitations';
import AppBar from '@material-ui/core/AppBar';
import Toolbar from '@material-ui/core/Toolbar';
import Container from '@material-ui/core/Container';
import BirdCard from './BirdCard';

const useStyles = makeStyles((theme) =>
  createStyles({
    card: {
      maxWidth: 345,
      [theme.breakpoints.down('xs')]: {
        maxWidth: 'none',
        width: '100%'
      }
    },
    media: {
      height: 250,
      backgroundPosition: 'top'
    },
    container: {
      marginTop: 80,
      [theme.breakpoints.down('xs')]: {
        marginTop: 60,
      }
    }
  })
);

export default function MediaCard() {
  const classes = useStyles();
  const [items, setItems] = useState(visitations);
  const [error, setError] = useState(null);
  const [isLoaded, setIsLoaded] = useState(false);

  // Note: the empty deps array [] means
  // this useEffect will run once
  // similar to componentDidMount()
  useEffect(() => {
    fetch("/visitations.json")
      .then(res => res.json())
      .then(
        (result) => {
          setIsLoaded(true);
          if(result.items.length > 0) {
            setItems(result.items);
          }
        },  
        // Note: it's important to handle errors here
        // instead of a catch() block so that we don't swallow
        // exceptions from actual bugs in components.
        (error) => {
          setIsLoaded(true);
          setError(error);
        }
      )
  }, [])

  return (
    <Grid container direction="row" spacing={1}>
      <Grid item xs={12}>
        <AppBar position="fixed">
          <Toolbar>
            <Typography variant="h6">
              Project Leroy
            </Typography>
          </Toolbar>
        </AppBar>
      </Grid>
      <Grid item xs={12}>
        <Container className={classes.container}>
          <Grid container spacing={3}>
            {
              items.map((visit, index) => { 
                return <BirdCard key={index} visit={visit}/> 
              })
            }
          </Grid>
        </Container>
      </Grid>
    </Grid>
  );
}
