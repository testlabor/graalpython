/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package com.oracle.graal.python.pegparser;

import org.junit.jupiter.api.Test;


public class BasicTests extends ParserTestBase {

    @Test
    public void assignment01() throws Exception {
        checkTreeResult("a: int = 2");
    }
    
//    @Test
//    public void booelan01() throws Exception {
//        checkTreeResult("True");
//    }
    
}
