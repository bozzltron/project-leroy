/* eslint-disable no-unused-expressions */
import React from 'react';
import { makeStyles, createStyles } from '@material-ui/core/styles';
import Card from '@material-ui/core/Card';
import CardActionArea from '@material-ui/core/CardActionArea';
import CardActions from '@material-ui/core/CardActions';
import CardContent from '@material-ui/core/CardContent';
import CardMedia from '@material-ui/core/CardMedia';
import Button from '@material-ui/core/Button';
import Typography from '@material-ui/core/Typography';
import Grid from '@material-ui/core/Grid';
import Modal from '@material-ui/core/Modal';
import Paper from '@material-ui/core/Paper';
import Container from '@material-ui/core/Container';

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
  modal: {
      overflowY: 'scroll',
      margin: "20px 20px 20px 20px",
      padding: "20px",
      [theme.breakpoints.down('xs')]: {
        margin: "10px 10px 10px 10px",
      },
      [theme.breakpoints.up('sm')]: {
        width: '600px',
        margin: "10px auto 10px auto"
      }
  },
  image: {
      width: "100%",
      boxSizing: "border-box",
      marginTop: '10px',
      [theme.breakpoints.down('xs')]: {
        
      }
  }
})
);

export default function BirdCard({visit}) {
    const classes = useStyles();
    const [open, setOpen] = React.useState(false);
    const path = window.location.href.includes("10.0.0.23") ? "" : "http://10.0.0.23";

    const handleOpen = () => {
      setOpen(true);
    };
  
    const handleClose = () => {
      setOpen(false);
    };
  
    return (    
      <Grid container item xs={12} sm={6} md={4} spacing={1}>
            <Card className={classes.card}>
            <CardActionArea>
                <CardMedia
                className={classes.media}
                image={path + visit.best_photo}
                title={visit.species}
                />
                <CardContent>
                <Typography gutterBottom variant="h5" component="h2">
                    {visit.species}
                </Typography>
                <Typography variant="body2" color="textSecondary" component="p">
                    {visit.records.length} photos <br />
                    <time>{visit.records[0].datetime}</time>
                    {visit.id}
                </Typography>
                </CardContent>
            </CardActionArea>
            <CardActions>
                <Button size="small" color="primary" onClick={handleOpen}>
                More Photos
                </Button>
                <Button size="small" color="primary">
                Tweet
                </Button>
            </CardActions>
            </Card>
            <Modal
                open={open}
                onClose={handleClose}
                className={classes.modal}
                aria-labelledby="simple-modal-title"
                aria-describedby="simple-modal-description"
                >
                <Paper>
                    <Container>
                        <Grid container spacing={3}>
                          <Grid item><img className={classes.image} src={visit.full_image} alt={visit.records[0].species}/></Grid> 
                            {
                                visit.records.map((record, index) => { 
                                  //return <Grid key={index} item><img className={classes.image} key={index} src={path + record.filename} alt={record.species}/></Grid> 
                                  return <img key={index} className={classes.image} key={index} src={path + record.filename} alt={record.species}/>   
                                })
                            }
                            
                        </Grid>
                    </Container>
                </Paper>
            </Modal>
        </Grid> 
      );
}